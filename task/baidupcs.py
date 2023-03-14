from os import makedirs


class BaiduPCS:
    def __init__(self, bduss, cookies):
        self.bduss = bduss
        self.cookies = cookies

    def list_shared_link_files(self, link, password=""):
        pass

    def save_shared_link(self, remote_path, link, password=""):
        pass

    def download_dir(self, remote_path, local_path):
        pass

    def download_file(self, path):
        pass

    def leech(self, shared_link, shared_password, remote_path, local_path):
        self.save_shared_link(remote_path, shared_link, shared_password)

        if not store_path.exists():
            makedirs(store_path, exists_ok=True)

        self.download_dir(remote_path, local_path)
