Prerequisites
===============

- Tezos

Mac:
Brew:

```
ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
````

External libs:
```
brew install hidapi libev wget
```

Install tezos:
```
git clone https://gitlab.com/tezos/tezos.git
cd tezos
git checkout latest-release
```

Install Ocaml:
```
brew install ocaml
wget https://github.com/ocaml/opam/releases/download/2.0.7/opam-2.0.7-x86_64-macOS
sudo mv opam-2.0.7-x86_64-macOS /usr/local/bin/opam
cd /usr/local/bin/
sudo chmod a+x opam
opam init
opam update
opam update
eval $(opam env)
opam switch create 4.09.1
eval $(opam env)
```

install Rust:
```
sudo wget https://sh.rustup.rs/rustup-init.sh
sudo chmod +x rustup-init.sh
./rustup-init.sh --profile minimal --default-toolchain 1.52.1 -y
source $HOME/.cargo/env
```

Compile Tezos:
```
cd ~/tezos
make build-deps
make
```

Generate node identity:
```
./tezos-node identity generate
```

Linux:

Install OPAM:
https://opam.ocaml.org/doc/Install.html

Install Tezos OPAM packages
```
wget -O latest-release:version.sh https://gitlab.com/tezos/tezos/raw/latest-release/scripts/version.sh
source latest-release:version.sh
opam switch create for_tezos $ocaml_version
eval $(opam env)
```

Get system dependencies and install binaries:
```
opam depext tezos
opam install tezos
```
