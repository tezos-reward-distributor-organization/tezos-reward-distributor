from unittest import TestCase

from cli.wallet_client_manager import WalletClientManager


class TestWalletClientManager(TestCase):
    def test_parse_get_manager_for_contract_response(self):
        response = """
                Disclaimer:
          The  Tezos  network  is  a  new  blockchain technology.
          Users are  solely responsible  for any risks associated
          with usage of the Tezos network.  Users should do their
          own  research to determine  if Tezos is the appropriate
          platform for their needs and should apply judgement and
          care in their network interactions.

        tz1PJnnddwa1P5jg5sChddigxfMccK8nwLiV (known as habanoz)
                """
        clientManager = WalletClientManager(None, node_addr=None)
        manager = clientManager.parse_get_manager_for_contract_response(response)
        self.assertEqual('tz1PJnnddwa1P5jg5sChddigxfMccK8nwLiV', manager)

    def test_parse_client_list_known_contracts_response(self):
        response = """
                Disclaimer:
          The  Tezos  network  is  a  new  blockchain technology.
          Users are  solely responsible  for any risks associated
          with usage of the Tezos network.  Users should do their
          own  research to determine  if Tezos is the appropriate
          platform for their needs and should apply judgement and
          care in their network interactions.

        newcontr: KT1XqEHigP5XumZy9i76QyVd6u93VD4HTqJK
        habanoz: tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio
        mainnetme: tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa
                """
        clientManager = WalletClientManager(None, node_addr=None)
        dict = clientManager.parse_list_known_contracts_response(response)

        self.assertTrue(dict['newcontr'] == 'KT1XqEHigP5XumZy9i76QyVd6u93VD4HTqJK')
        self.assertTrue(dict['habanoz'] == 'tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio')
        self.assertTrue(dict['mainnetme'] == 'tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa')

    def test_parse_list_known_addresses_response(self):
        response = """
                        Disclaimer:
                  The  Tezos  network  is  a  new  blockchain technology.
                  Users are  solely responsible  for any risks associated
                  with usage of the Tezos network.  Users should do their
                  own  research to determine  if Tezos is the appropriate
                  platform for their needs and should apply judgement and
                  care in their network interactions.

                mainpay: tz1aZoFH2pd3V9UEq5psqVokVBYkt7YSi1ow
                habanoz: tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio (unencrypted sk known)
                mainnetme: tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa (tcp sk known)
                zeronetme: tz1MZ72sJEVen3Qgc7uWvqKhKFJW84bNGd6T (unencrypted sk not known)
                baker: tz1XXXXXXXX (unix sk known)
                        """

        clientManager = WalletClientManager(None, node_addr=None)
        dict = clientManager.parse_list_known_addresses_response(response)

        habanoz = dict['tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio']

        self.assertEqual(habanoz['alias'], 'habanoz')
        self.assertEqual(habanoz['sk'], True)

        mainnetme = dict['tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa']

        self.assertEqual(mainnetme['alias'], 'mainnetme')
        self.assertEqual(mainnetme['sk'], True)

        zeronetme = dict['tz1MZ72sJEVen3Qgc7uWvqKhKFJW84bNGd6T']

        self.assertEqual(zeronetme['alias'], 'zeronetme')
        self.assertEqual(zeronetme['sk'], False)

        mainpay = dict['tz1aZoFH2pd3V9UEq5psqVokVBYkt7YSi1ow']

        self.assertEqual(mainpay['alias'], 'mainpay')
        self.assertEqual(mainpay['sk'], False)

        baker = dict['tz1XXXXXXXX']
        self.assertEqual(baker['alias'], 'baker')
        self.assertEqual(baker['sk'], True)
