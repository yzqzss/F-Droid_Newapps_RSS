import dataclasses

@dataclasses.dataclass
class RepoConfig:
    id: str # same as object name, used in filename
    name: str
    json_url: str
    web_public_subdir: str
    package_details_url: str
    package_homepage_url: str

@dataclasses.dataclass
class Repos:
    fdroid =  RepoConfig(
        id = 'fdroid',
        name = 'F-Droid',
        json_url='https://f-droid.org/repo/index-v2.json',
        web_public_subdir='', # 'fdroid/'
        package_details_url='https://f-droid.org/packages/',
        package_homepage_url='https://f-droid.org/packages/',
    )
    izzyondroid = RepoConfig(
        id = 'izzyondroid',
        name = 'IzzyOnDroid',
        json_url='https://apt.izzysoft.de/fdroid/repo/index-v2.json',
        web_public_subdir='izzyondroid/',
        package_details_url='https://apt.izzysoft.de/fdroid/index/apk/',
        package_homepage_url='https://apt.izzysoft.de/fdroid/',
    )

    def __iter__(self):
        yield self.fdroid
        yield self.izzyondroid

repos = Repos()