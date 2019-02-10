from unittest import TestCase

from util.client_utils import parse_list_known_addresses_response, parse_get_manager_for_contract_response, \
    parse_client_list_known_contracts_response


class TestParse_client_utils(TestCase):
    def test_parse_list_known_addresses_response(self):
        response = """
                Disclaimer:
          The  Tezos  network  is  a  new  blockchain technology.
          Users are  solely responsible  for any risks associated
          with usage of the Tezos network.  Users should do their
          own  research to determine  if Tezos is the appropriate
          platform for their needs and should apply judgement and
          care in their network interactions.

        habanoz: tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio (unencrypted sk known)
        mainnetme: tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa (tcp sk known)
        zeronetme: tz1MZ72sJEVen3Qgc7uWvqKhKFJW84bNGd6T (unencrypted sk not known)
                """

        dict = parse_list_known_addresses_response(response)

        habanoz = dict['tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio']

        self.assertEqual(habanoz['alias'], 'habanoz')
        self.assertEqual(habanoz['sk'], True)
        self.assertEqual(habanoz['pkh'], 'tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio')

        mainnetme = dict['tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa']

        self.assertEqual(mainnetme['alias'], 'mainnetme')
        self.assertEqual(mainnetme['sk'], True)
        self.assertEqual(mainnetme['pkh'], 'tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa')

        zeronetme = dict['tz1MZ72sJEVen3Qgc7uWvqKhKFJW84bNGd6T']

        self.assertEqual(zeronetme['alias'], 'zeronetme')
        self.assertEqual(zeronetme['sk'], False)
        self.assertEqual(zeronetme['pkh'], 'tz1MZ72sJEVen3Qgc7uWvqKhKFJW84bNGd6T')

    def test_get_manager(self):
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

        manager = parse_get_manager_for_contract_response(response)
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

        dict = parse_client_list_known_contracts_response(response)
        self.assertTrue(dict['newcontr']=='KT1XqEHigP5XumZy9i76QyVd6u93VD4HTqJK')
        self.assertTrue(dict['habanoz']=='tz1fyvFH2pd3V9UEq5psqVokVBYkt7rHTKio')
        self.assertTrue(dict['mainnetme']=='tz1a5GGJeyqeQ4ihZqbiRVcvj5rY5kMAt3Xa')