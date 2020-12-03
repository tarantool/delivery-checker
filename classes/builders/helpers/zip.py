import os
import zipfile


class Zip:
    def __zip_one(self, fp, path, rel_dir='.'):
        rel_path = os.path.relpath(path, rel_dir)
        if rel_path != '.':
            fp.write(path, rel_path)

    def __zip_all(self, fp, path, rel_dir='.'):
        if os.path.isdir(path):
            for root, sub_dirs, files in os.walk(path):
                for sub_dir in sub_dirs:
                    self.__zip_one(fp, os.path.join(root, sub_dir), rel_dir)
                for file in files:
                    self.__zip_one(fp, os.path.join(root, file), rel_dir)
        else:
            self.__zip_one(fp, path, rel_dir)

    def zip_path(self, path, rel_dir='.', zip_name='output.zip'):
        fp = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
        self.__zip_all(fp, path, rel_dir)
        fp.close()

    def zip_paths(self, paths, rel_dir='.', zip_name='output.zip'):
        fp = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
        for path in paths:
            self.__zip_all(fp, path, rel_dir)
        fp.close()
