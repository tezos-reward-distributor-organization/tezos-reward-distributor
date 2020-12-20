# Plugins

The Tezos Reward Distributor uses a plugin style subsystem for sending out payment notifications.

Each plugin and its configuration are detailed out below. Some plugins may require additional libraries that are not installed with TRD.

The configuration parameters for all plugins are located in the bakers .yaml config file. Please take a look at [the example config](https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/blob/master/examples/tz1boot1pK9h2BVGXdyvfQSv8kd1LQM6H889.yaml).

Individual plugins will not load if not properly configured.

You must specify which plugins to enable by adding their name to the "enabled" list. No plugins are enabled by default.

In this example, even though the webhook plugin is properly configured, it is *not* listed in the 'enabled' section, and therefor will not activate.

```
plugins:
  enabled:
  webhook:
    endpoint: https://mydomain.com/webhook.php
    token: Xynl6svphysd3BhjLP6IS
```

In order to activate the webhook plugin, you must add the name of the plugin to the *enabled* section as shown here:

```
plugins:
  enabled:
  - webhook
  webhook:
    endpoint: https://mydomain.com/webhook.php
    token: Xynl6svphysd3BhjLP6IS
```

If that doesn't make sense to you, please read the [YAML format documentation](https://yaml.org/spec/history/2001-05-26.html).

---

## Email Plugin

This plugin will send the configured recipients an email of payouts status with a CSV report attached.

### Parameters

* smtp_user: The username for SMTP authentication
* smtp_pass: The password or application token for SMTP authentication
* smtp_host: The host of your SMTP server
* smtp_port: The port for communication to your SMTP server. TLS uses 587.
* smtp_tls: true/false. Only TLS is supported as SSL is usually deprecated in email servers.
* smtp_sender: The address for 'From' in the email
* smtp_recipients: A YAML list containing email addresses of intended recipients. Must be list format even if 1 recipient.

### Example Config

```
plugins:
  email:
    smtp_user: user@domain.com
    smtp_pass: horsebatterystaple2
    smtp_host: smtp.domain.com
    smtp_port: 587
    smtp_tls: true
    smtp_sender: trdnotice@domain.com
    smtp_recipients:
      - bob@domain.com
      - alice@hotmail.com
```

## Telegram Plugin

This plugin allows payouts notifications to be sent via Telegram bot to specific chatIds, including groups.

You must first create a Telegram bot to generate the *bot_api_key* and you must discover your, or your groups', *chat_id*. There are many guides/tutorials on the internet for how to do this.

The Telegram plugin does not need read access to any messages and the bot will not respond to any commands. This is a "send only" style of bot.

### Parameters

* chat_ids: A YAML list containing chat IDs of users and/or group IDs for groups. Group IDs typically start with a - (negative/dash) symbol. Must be list format even if only 1 ID.
* bot_api_key: This is the API token that you get from @TheBotFather after creating your bot.

### Example Config

```
plugins:
  telegram:
    chat_ids:
      - 123456789
      - -13134455
    bot_api_key: 988877766:SKDJFLSJDFJLJSKDFJLKSDJFLKJDF
```

## Twitter Plugin

This plugin allows payout notifications to be sent via a Twitter tweet. This plugin does not read existing tweets, or read any DMs. The plugin supports adding hashtags to your tweet. The plugin posts tweets "as you", meaning your @-handle will be the author of the post. No other information is submitted to the tweet.

Follow this outline to generate the API tokens and secrets for the plugin:

1. Sign up as a developer at https://developer.twitter.com/
2. Create a Twitter app
3. Enable Read and Write permissions on the app
4. Under 'Keys and Tokens' there are two sections: Consumer Keys, and Authentication Tokens
	* Under 'Consumer Keys', generate 'API Key and Secret'
	* Under 'Authentication Tokens', generate 'Access Token & Secret'
	* You can ignore 'Bearer Token'

You must also install an additional Python library, [tweepy](https://github.com/tweepy/tweepy)

```
pip3 install -u tweepy
```

### Example Config

**NOTE**: All 4 pieces of keys and tokens are required.

**NOTE**: Hashtags *must* include '#' and *must* be inside quotation "" marks

```
plugins:
  twitter:
    api_key: XXXXXXXX
    api_secret: ZZZZZZZZ
    access_token: YYYYYYYY
    access_secret: WWWWWWWW
    extra_tags:
      - "#our_baker"
      - "#tezos"
      - "#rewards"
```

## Webhook Plugin

This plugin makes an HTTP POST request to an endpoint. This endpoint will receive a JSON object containing the reward data.

For simple security, configure a random token (alphanumeric string) to be included in the root JSON object. Your receiver script should verify this token before accepting data.

Your script can return a short message in the response body. This will be displayed on the TRD console and written to the TRD logs.

### Example JSON Object

"payouts" is a JSON array of objects, each object representing the status of a payout. All Tez amounts are in mutez.

```
{
  "timestamp": 1604982374,
  "token": "Xynl6svphysd3BhjLP6IS",
  "payouts": [
    {
      "address": "tz1LrHNbbCLgNJZsEsTUYFvWz2THgJC8fHyX",
      "paymentAddress": "tz1LrHNbbCLgNJZsEsTUYFvWz2THgJC8fHyX",
      "addressType": "D",
      "cycle": 415,
      "stakingBalance": 65116664916,
      "ratio": 0.16080255,
      "feeRatio": 0.01398283,
      "amount": 207756875,
      "feeAmount": 18065815,
      "feeRate": 0.08,
      "payable": true,
      "skipped": false,
      "opHash": "oo4Gikxyj8cMqM8xzgWxqnsxXoGwfhZqHDrLqpA6ENmMVoYUnVd",
      "neededActivation": false,
      "paymentStatus": "DONE"
    },
    {...}
  ]
}
```

### Example Config

```
plugins:
  webhook:
    endpoint: https://mydomain.com/webhook.php
    token: Xynl6svphysd3BhjLP6IS
```
