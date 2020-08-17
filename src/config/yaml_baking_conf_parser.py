from config.yaml_conf_parser import YamlConfParser


class BakingYamlConfParser(YamlConfParser):
    def __init__(self, yaml_text, wllt_clnt_mngr, provider_factory, verbose=None,
                 block_api=None) -> None:
        super().__init__(yaml_text, verbose)
        self.wllt_clnt_mngr = wllt_clnt_mngr
        if block_api is None:
            block_api = provider_factory.newBlockApi()
        self.block_api = block_api

    def parse(self):
        yaml_conf_dict = super().parse()
        self.set_conf_obj(yaml_conf_dict)
