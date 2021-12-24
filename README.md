# Misskey Updaeter Bot(MUB)

## 使い方

Misskey Updater Bot(mub)をインストールします

```bash
python setup.py sdist
cd dist && pip install mub-0.0.1.tar.gz
```

config.ini を作ります

```ini
[BOT]
token=botにするユーザーのトークン
url=インスタンスに対するwebsocket url (wss://example.com/streaming)

[Misskey]
path=インスタンスがあるフルパス
```

使う

```bash
mub --config ./config.ini
```