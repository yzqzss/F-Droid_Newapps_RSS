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
    if r.headers.get('Etag', ' ') != etag:
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
    sys.exit(0) if not os.path.exists('devmode') else None

with open(json_file_to_load, 'r') as f:
    print(f'Parsing JSON...')
    data = json.load(f)

print('Selecting packages...')
packages = data.get('packages', {})
print('Removing old packages...')
new_packages = {}
for package_name in packages:
    package = packages[package_name]
    if package['metadata']['added']/1000 > now - 60*60*24*30:
        # print(package_name)
        new_packages.update({package_name: package})

print('Sorting new packages...1')
# newest first
# package["metadata"]["added"]
new_packages_names = list(new_packages)
new_packages_added = [new_packages[package_name]['metadata']['added'] for package_name in new_packages_names]
new_packages_added, new_packages_names = zip(*sorted(zip(new_packages_added, new_packages_names), reverse=True))
print('Sorting new packages...2')
sorted_new_packages = {}
for package_name in new_packages_names:
    print(new_packages[package_name]['metadata']['added'], package_name)
    sorted_new_packages.update({package_name: new_packages[package_name]})
print(len(sorted_new_packages))

with open('new_apps.json', 'w') as f:
    print(f'Saving JSON to new_apps.json...')
    json.dump(sorted_new_packages, f, ensure_ascii=False, indent=4)
    print('Done.')


os.makedirs('feed/', exist_ok=True)

from languages_config import langs
for lang in langs:
    primary_lang = lang.split('-')[0]
    area_lang = lang.split('-')[1] if len(lang.split('-')) > 1 else None
    print('Generating ATOM feed...', lang)
    feed = FeedGenerator()
    feed.title(f'New apps on F-Droid ({lang})')
    feed.description(f'New apps on F-Droid ({lang})')
    feed.id(f'https://newapps.f-droid.othing.xyz/new_apps.{lang}.xml')
    feed.link( href=f'https://newapps.f-droid.othing.xyz/new_apps.{lang}.xml', rel='self' )
    feed.link(href='https://f-droid.org/packages/', rel='alternate')
    feed.author({'name': 'yzqzss', 'email': 'yzqzss@yandex.com'})
    feed.language(lang)
    for package_name in sorted_new_packages:
        print(package_name)
        package = sorted_new_packages[package_name]
        entry = feed.add_entry(order='append')
        entry.id(f'https://f-droid.org/packages/{package_name}/')
        entry.pubDate(datetime.datetime.fromtimestamp(package['metadata']['added']/1000, tz=datetime.timezone.utc))
        entry.updated(datetime.datetime.fromtimestamp(package['metadata']['lastUpdated']/1000, tz=datetime.timezone.utc))
        entry.author(name=package['metadata'].get('authorName', ''))
    
        title = package['metadata']['name'].get(lang, None)
        if title is None:
            title_langs = list(package['metadata']['name'].keys())
            # fallback to same language, but different area
            if area_lang is not None:
                for title_lang in title_langs:
                    if title_lang.split('-')[0] == primary_lang:
                        title = package['metadata']['name'][title_lang]
                        break
            # fallback to English, en-US first
            if title is None:
                if 'en-US' in title_langs:
                    title = package['metadata']['name']['en-US']
                for title_lang in title_langs:
                    if title_lang.split('-')[0] == 'en':
                        title = package['metadata']['name'][title_lang]
                        break
            # fallback to first key
            if title is None:
                title = package['metadata']['name'][title_langs[0]]
        assert title is not None
        entry.title(title)

        entry.link(href=f'https://f-droid.org/packages/{package_name}/')

        # ATOM summary == F-Droid summary
        description = package['metadata'].get('summary', None) # some app has no summary
        if description is not None:
            description = description.get(lang, None)
            if description is None:
                desc_langs = list(package['metadata']['summary'].keys())
                # fallback to same language, but different area
                if area_lang is not None:
                    for desc_lang in desc_langs:
                        if desc_lang.split('-')[0] == primary_lang:
                            description = package['metadata']['summary'][desc_lang]
                            break
                # fallback to English, en-US first
                if description is None:
                    if 'en-US' in desc_langs:
                        description = package['metadata']['summary']['en-US']
                    for desc_lang in desc_langs:
                        if desc_lang.split('-')[0] == 'en':
                            description = package['metadata']['summary'][desc_lang]
                            break
                # fallback to firsr key
                if description is None:
                    description = package['metadata']['summary'][list(package['metadata']['summary'].keys())[0]]
        entry.summary(description if description else 'No summary.') # ATOM
        entry.description(description if description else 'No summary.', isSummary=False) # RSS

        # ATOM content == F-Droid description
        content = package['metadata'].get('description', None)
        if content is not None:
            content = content.get(lang, None)
            if content is None:
                content_langs = list(package['metadata']['description'].keys())
                # fallback to same language, but different area
                if area_lang is not None:
                    for content_lang in content_langs:
                        if content_lang.split('-')[0] == primary_lang:
                            content = package['metadata']['description'][content_lang]
                            break
                # fallback to English, en-US first
                if content is None:
                    if 'en-US' in content_langs:
                        content = package['metadata']['description']['en-US']
                    for content_lang in content_langs:
                        if content_lang.split('-')[0] == 'en':
                            content = package['metadata']['description'][content_lang]
                            break
                # fallback to firsr key
                content = package['metadata']['description'][list(package['metadata']['description'].keys())[0]]
        if isinstance(content, str):
            content = content.replace('\n', '<br>')
        content = content if content else 'No description.'
        entry.content(content, type='html')
    feed.atom_file(f'feed/new_apps.{lang}.xml', pretty=True)
    feed.rss_file(f'feed/new_apps.{lang}.rss.xml', pretty=True)

with open('index_template.html', 'r') as f:
    index_template = f.read()
html_body = ''
for lang in langs:
    html_body += f'<a href="new_apps.{lang}.xml">{lang} ATOM</a> (suggest) <br>\n'
    html_body += f'<a href="new_apps.{lang}.rss.xml">{lang} RSS</a><br>\n'
with open('feed/index.html', 'w') as f:
    f.write(index_template.replace('{{body}}', html_body))

print('Done.')
