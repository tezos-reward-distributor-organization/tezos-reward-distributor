import requests
from http import HTTPStatus
from time import sleep
from pprint import pformat
from json import JSONDecodeError

from Constants import VERSION, TZKT_PUBLIC_API_URL, MAX_SEQUENT_CALLS
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger

logger = main_logger


class TzKTApiError(ApiProviderException):
    pass


MAX_PAGE_SIZE = 10000
TZKT_REQUEST_BUFFER_SECONDS = 0.5
TZKT_RETRY_TIMEOUT_SECONDS = 2.0


class TzKTApi:
    max_page_size = MAX_PAGE_SIZE
    delay_between_calls = TZKT_REQUEST_BUFFER_SECONDS  # in seconds

    def __init__(self, base_url, timeout):
        self.base_url = base_url
        self.timeout = timeout

    @staticmethod
    def from_network(network, timeout=30):
        """
        Create new API instance
        :param network: one of `mainnet`, current testnet
        :param timeout: request timeout in seconds (default = 30)
        """
        base_urls = TZKT_PUBLIC_API_URL
        assert network in base_urls, f"Unsupported network {network}"
        return TzKTApi(base_url=base_urls[network], timeout=timeout)

    @staticmethod
    def from_url(base_url, timeout=30):
        """
        Create new API instance
        :param base_url: base API url, i.e. http://localhost:5000/v1
        :param timeout: request timeout in seconds (default = 30)
        """
        return TzKTApi(base_url=base_url, timeout=timeout)

    def _request(self, path, **params):
        data = {key: value for key, value in params.items() if value is not None}

        if path.startswith("/"):
            url = self.base_url + path
        else:
            url = self.base_url + "/" + path

        verbose_logger.debug("Requesting {}".format(url))

        try:
            response = requests.get(
                url=url,
                params=data,
                timeout=self.timeout,
                headers={"User-Agent": f"trd-{VERSION}"},
            )
        except requests.Timeout:
            raise TzKTApiError("Request timeout")
        except requests.ConnectionError:
            raise TzKTApiError("DNS lookup failed")
        except requests.HTTPError as e:
            raise TzKTApiError("HTTP Error occurred: {}".format(e))
        except requests.RequestException as e:
            raise TzKTApiError(e)

        # Raise exception for client side errors (4xx)
        if (
            HTTPStatus.BAD_REQUEST
            <= response.status_code
            < HTTPStatus.INTERNAL_SERVER_ERROR
        ):
            raise TzKTApiError(
                f"TzKT returned {response.status_code} error:\n{response.text}"
            )

        # Return None if empty content
        # or we get a server side error (5xx)
        if (response.status_code == HTTPStatus.NO_CONTENT) or (
            response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
        ):
            return None

        try:
            res = response.json()
        except JSONDecodeError:
            raise TzKTApiError(f"Failed to decode JSON:\n{response.text}")

        verbose_logger.debug(f"Response from TzKT is:\n{pformat(res)}")

        return res

    def get_current_cycle(self):
        return self.get_head()["cycle"]

    def get_current_level(self):
        return self.get_head()["level"]

    def get_head(self) -> dict:
        """
        Returns indexer head and synchronization status.
        :return: {
            "level": 0,
            "hash": "string",
            "protocol": "string",
            "timestamp": "2020-06-08T15:33:07Z",
            "knownLevel": 0,
            "lastSync": "2020-06-08T15:33:07Z",
            "synced": true
        }
        """
        return self._request("head")

    def get_reward_split(self, address, cycle, fetch_delegators=True) -> dict:
        """
        Returns baker rewards for the specified cycle with all delegator balances at that cycle
        to allow rewards distribution in proportion to shares.
        :param address: Baker address
        :param cycle: Rewards cycle
        :param fetch_delegators: Load snapshotted balances for all delegators
        :returns: {
            "cycle": 0,
            "stakingBalance": 0,
            "delegatedBalance": 0,
            "numDelegators": 0,
            "expectedBlocks": 0,
            "expectedEndorsements": 0,
            "futureBlocks": 0,
            "futureBlockRewards": 0,
            "futureBlockDeposits": 0,
            "ownBlocks": 0,
            "ownBlockRewards": 0,
            "extraBlocks": 0,
            "extraBlockRewards": 0,
            "missedOwnBlocks": 0,
            "missedOwnBlockRewards": 0,
            "missedExtraBlocks": 0,
            "missedExtraBlockRewards": 0,
            "uncoveredOwnBlocks": 0,
            "uncoveredOwnBlockRewards": 0,
            "uncoveredExtraBlocks": 0,
            "uncoveredExtraBlockRewards": 0,
            "blockDeposits": 0,
            "futureEndorsements": 0,
            "futureEndorsementRewards": 0,
            "futureEndorsementDeposits": 0,
            "endorsements": 0,
            "endorsementRewards": 0,
            "missedEndorsements": 0,
            "missedEndorsementRewards": 0,
            "uncoveredEndorsements": 0,
            "uncoveredEndorsementRewards": 0,
            "endorsementDeposits": 0,
            "ownBlockFees": 0,
            "extraBlockFees": 0,
            "missedOwnBlockFees": 0,
            "missedExtraBlockFees": 0,
            "uncoveredOwnBlockFees": 0,
            "uncoveredExtraBlockFees": 0,
            "doubleBakingRewards": 0,
            "doubleBakingLostDeposits": 0,
            "doubleBakingLostRewards": 0,
            "doubleBakingLostFees": 0,
            "doubleEndorsingRewards": 0,
            "doubleEndorsingLostDeposits": 0,
            "doubleEndorsingLostRewards": 0,
            "doubleEndorsingLostFees": 0,
            "revelationRewards": 0,
            "revelationLostRewards": 0,
            "revelationLostFees": 0,
            "delegators": [
                {
                    "address": "string",
                    "balance": 0,
                    "emptied": true,
                    "currentBalance": 0
                }
            ]
        }
        """
        res = None
        offset = 0
        limit = self.max_page_size if fetch_delegators else 0

        for call_count in range(MAX_SEQUENT_CALLS):
            page = self._request(
                f"rewards/split/{address}/{cycle}", offset=offset, limit=limit
            )

            if page is None:
                verbose_logger.warning(
                    f"Retry getting rewards/split/{address}/{cycle} ({call_count}) ..."
                )
                sleep(TZKT_RETRY_TIMEOUT_SECONDS)
                continue

            assert isinstance(page, dict) and "delegators" in page

            if res is None:
                res = page
            else:
                assert isinstance(res, dict) and "delegators" in res
                res["delegators"].extend(page["delegators"])

            if not fetch_delegators or len(res["delegators"]) >= res["numDelegators"] or len(page["delegators"]) == 0:
                return res
            else:
                offset += limit
                sleep(self.delay_between_calls)

        raise TzKTApiError(f"Max sequent calls number exceeded ({MAX_SEQUENT_CALLS})")

    def get_account_by_address(self, address) -> dict:
        """
        Returns an account with the specified address.
        :param address: Account address (starting with tz or KT)
        :return: {
            "type": "user",
            "alias": "string",
            "address": "string",
            "publicKey": "string",
            "revealed": true,
            "balance": 0,
            "counter": 0,
            "delegate": {
                "alias": "string",
                "address": "string",
                "active": true
            },
            "delegationLevel": 0,
            "delegationTime": "2020-06-08T15:33:06Z",
            "numContracts": 0,
            "numActivations": 0,
            "numDelegations": 0,
            "numOriginations": 0,
            "numTransactions": 0,
            "numReveals": 0,
            "numMigrations": 0,
            "firstActivity": 0,
            "firstActivityTime": "2020-06-08T15:33:06Z",
            "lastActivity": 0,
            "lastActivityTime": "2020-06-08T15:33:06Z",
            "contracts": [
                {}
            ],
            "operations": [
                {
                "type": "string"
                }
            ],
            "metadata": {
                "address": "string",
                "kind": "string",
                "owner": "string",
                "alias": "string",
                "description": "string",
                "logo": "string",
                "site": "string",
                "support": "string",
                "email": "string",
                "twitter": "string",
                "telegram": "string",
                "discord": "string",
                "reddit": "string",
                "slack": "string",
                "riot": "string",
                "github": "string"
            }
        }
        """
        return self._request(f"accounts/{address}")

    def get_protocol_by_cycle(self, cycle: int) -> dict:
        """
        Returns actual protocol for a particular cycle.
        :param cycle: Cycle
        :return: {
            "code": 6,
            "hash": "PsCARTHAGazKbHtnKfLzQg3kms52kSRpgnDY982a9oYsSXRLQEb",
            "firstLevel": 851969,
            "constants": {
                "preservedCycles": 5,
                "blocksPerCycle": 4096,
                "blocksPerCommitment": 32,
                "blocksPerSnapshot": 256,
                "blocksPerVoting": 32768,
                "timeBetweenBlocks": 60,
                "endorsersPerBlock": 32,
                "hardOperationGasLimit": 1040000,
                "hardOperationStorageLimit": 60000,
                "hardBlockGasLimit": 10400000,
                "tokensPerRoll": 8000000000,
                "revelationReward": 125000,
                "blockDeposit": 512000000,
                "blockReward": [
                    1250000,
                    187500
                ],
                "endorsementDeposit": 64000000,
                "endorsementReward": [
                    1250000,
                    833333
                ],
                "originationSize": 257,
                "byteCost": 1000
            },
            "metadata": {
                "alias": "Carthage",
                "docs": "https://tezos.gitlab.io/protocols/006_carthage.html"
            }
        }
        """
        return self._request(f"protocols/cycles/{cycle}")

    def get_snapshot_level(self, cycle):
        return self._request(f"cycles/{cycle}")["snapshotLevel"]
