import requests
import json
import tqdm
import sys
from feedgen.feed import FeedGenerator
import os
import io
import datetime
import time

today = datetime.date.today().strftime('%Y%m%d')
now = time.time()
json_file_to_load = f'index-v2.cache.json'
etag_file = f'index-v2.etag.txt'
etag = ''
if os.path.exists(etag_file):
    with open(etag_file, 'r') as f:
        etag = f.read()

def update_index():
    print(f'Fetching JSON from F-Droid...')
    tqdmd = tqdm.tqdm(unit='B', unit_scale=True, desc='Fetching JSON from F-Droid')
    json_url = 'https://f-droid.org/repo/index-v2.json'
    r = requests.get(json_url, stream=True)
    if r.headers.get('Etag', ' ') != etag and os.path.exists(json_file_to_load) is False:
        data_io = io.BytesIO()
        for chunk in r.iter_content(chunk_size=1024):
            tqdmd.update(len(chunk))
            data_io.write(chunk)
        tqdmd.close()
        print(f'Parsing JSON...')
        data = json.loads(data_io.getvalue())
        print(f'Saving JSON to {json_file_to_load}...')
        with open(f'_tmp.json', 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.rename('_tmp.json', json_file_to_load)
        with open(etag_file, 'w') as f:
            f.write(r.headers.get('Etag', ''))
        return True
    return False

if update_index() is False:
    print('No new packages.')
    sys.exit(0)

with open(json_file_to_load, 'r') as f:
    print(f'Parsing JSON...')
    data = json.load(f)

print('Selecting packages...')
packages = data.get('packages', {})
print('Removing old packages...')
new_packages = {}
for package_name in packages:
    package = packages[package_name]
    if package['metadata']['added']/1000 > now - 60*60*24*30*14:
        print(package_name)
        new_packages.update({package_name: package})

print('Sorting new packages...1')
# newest first
# package["metadata"]["added"]
new_packages_names = list(new_packages)
new_packages_added = [new_packages[package_name]['metadata']['added'] for package_name in new_packages_names]
new_packages_added, new_packages_names = zip(*sorted(zip(new_packages_added, new_packages_names), reverse=False))
print('Sorting new packages...2')
sorted_new_packages = {}
for package_name in new_packages_names:
    print(package_name, new_packages[package_name]['metadata']['added'])
    sorted_new_packages.update({package_name: new_packages[package_name]})
print(len(new_packages_names))

with open('new_apps.json', 'w') as f:
    print(f'Saving JSON to new_apps.json...')
    json.dump(sorted_new_packages, f, ensure_ascii=False, indent=4)
    print('Done.')

from languages_config import langs
for lang in langs:
    print('Generating RSS feed...', lang)
    feed = FeedGenerator()
    feed.title('New apps on F-Droid')
    feed.description('New apps on F-Droid')
    feed.link(href='https://f-droid.org/en/packages/')
    feed.language(lang)
    for package_name in sorted_new_packages:
        package = sorted_new_packages[package_name]
        entry = feed.add_entry()
        entry.guid(package_name, permalink=True)
        entry.pubDate(datetime.datetime.fromtimestamp(package['metadata']['added']/1000, tz=datetime.timezone.utc))
        entry.updated(datetime.datetime.fromtimestamp(package['metadata']['lastUpdated']/1000, tz=datetime.timezone.utc))
        entry.author(name=package['metadata'].get('authorName', ''))
        title = package['metadata']['name'].get(lang, None)
        if title is None:
            # fallback to firsr key
            title = package['metadata']['name'][list(package['metadata']['name'].keys())[0]]
        entry.title(title)
        entry.link(href=f'https://f-droid.org/en/packages/{package_name}/')
        # RSS description == F-Droid summary
        description = package['metadata'].get('summary', None)
        if description is not None:
            description = description.get(lang, None)
            if description is None:
                # fallback to firsr key
                description = package['metadata']['summary'][list(package['metadata']['summary'].keys())[0]]
        entry.description(description, isSummary=True)
        # RSS content == F-Droid description
        content = package['metadata'].get('description')
        if content is not None:
            content = content.get(lang, None)
            if content is None:
                # fallback to firsr key
                content = package['metadata']['description'][list(package['metadata']['description'].keys())[0]]
        entry.content(content)
    os.makedirs('rss', exist_ok=True)
    feed.rss_file(f'rss/new_apps.{lang}.xml', pretty=True)