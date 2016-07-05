import datetime
import os
import re
import time

from salts_lib import kodi
from salts_lib import log_utils
from salts_lib import utils2
from salts_lib.constants import FORCE_NO_MATCH
from salts_lib.constants import VIDEO_TYPES

__all__ = ['scraper', 
'proxy', 
'local_scraper', 
'pw_scraper', 
'nitertv_scraper',
           'movieshd_scraper', 
		   'hdflix_scraper',
           'fmovie_scraper', 
		   'piratejunkies_scraper', 
		   'kiwihd_scraper', 
		   'watch5s_scraper',
           'dizibox_scraper',
           'stage66_scraper',
           'xmovies8_scraper', 
		   'vivoto_scraper', 
		   'moviexk_scraper',
           'pubfilm_scraper', 
		   'pelispedia_scraper',
           'dizilab_scraper', 
		   'dizimag_scraper',
		   'moviebox_scraper',
		   'm4ufree_scraper',
		   'serieswatch_scraper',
           'dizigold_scraper', 
		   'emoviespro_scraper', 
		   '123movies_scraper', 
		   'sezonlukdizi_scraper',
           'yesmovies_scraper',
		   'moviego_scraper',
		   'hevcbluray_scraper',
           'miradetodo_scraper', 
		   'xmovies8v2_scraper', 
		   'rainierland_scraper',
		   'vu45_scraper',
           'afdahorg_scraper', 
		   'farda_scraper', 
		   'hdmovie14_scraper', 
		   'dayt_scraper',
           'moviesub_scraper', 
		   'cloudmovie_scraper']

from . import *
    
class ScraperVideo:
    def __init__(self, video_type, title, year, trakt_id, season='', episode='', ep_title='', ep_airdate=''):
        assert(video_type in (VIDEO_TYPES.__dict__[k] for k in VIDEO_TYPES.__dict__ if not k.startswith('__')))
        self.video_type = video_type
        if isinstance(title, unicode): self.title = title.encode('utf-8')
        else: self.title = title
        self.year = str(year)
        self.season = season
        self.episode = episode
        if isinstance(ep_title, unicode): self.ep_title = ep_title.encode('utf-8')
        else: self.ep_title = ep_title
        self.trakt_id = trakt_id
        self.ep_airdate = None
        if ep_airdate:
            try: self.ep_airdate = datetime.datetime.strptime(ep_airdate, "%Y-%m-%d").date()
            except (TypeError, ImportError): self.ep_airdate = datetime.date(*(time.strptime(ep_airdate, '%Y-%m-%d')[0:3]))

    def __str__(self):
        return '|%s|%s|%s|%s|%s|%s|%s|' % (self.video_type, self.title, self.year, self.season, self.episode, self.ep_title, self.ep_airdate)

def update_xml(xml, new_settings, cat_count):
    new_settings.insert(0, '<category label="Scrapers %s">' % (cat_count))
    new_settings.append('    </category>')
    new_settings = '\n'.join(new_settings)
    match = re.search('(<category label="Scrapers %s">.*?</category>)' % (cat_count), xml, re.DOTALL | re.I)
    if match:
        old_settings = match.group(1)
        if old_settings != new_settings:
            xml = xml.replace(old_settings, new_settings)
    else:
        log_utils.log('Unable to match category: %s' % (cat_count), log_utils.LOGWARNING)
    return xml

def update_settings():
    full_path = os.path.join(kodi.get_path(), 'resources', 'settings.xml')
    
    try:
        # open for append; skip update if it fails
        with open(full_path, 'a') as f:
            pass
    except Exception as e:
        log_utils.log('Dynamic settings update skipped: %s' % (e), log_utils.LOGWARNING)
    else:
        with open(full_path, 'r') as f:
            xml = f.read()

        new_settings = []
        cat_count = 1
        old_xml = xml
        classes = scraper.Scraper.__class__.__subclasses__(scraper.Scraper)  # @UndefinedVariable
        classes += proxy.Proxy.__class__.__subclasses__(proxy.Proxy)  # @UndefinedVariable
        for cls in sorted(classes, key=lambda x: x.get_name().upper()):
            if not cls.get_name() or cls.has_proxy(): continue
            new_settings += cls.get_settings()
            if len(new_settings) > 90:
                xml = update_xml(xml, new_settings, cat_count)
                new_settings = []
                cat_count += 1
    
        if new_settings:
            xml = update_xml(xml, new_settings, cat_count)
    
        if xml != old_xml:
            with open(full_path, 'w') as f:
                f.write(xml)
        else:
            log_utils.log('No Settings Update Needed', log_utils.LOGDEBUG)


def update_all_scrapers():
        try: last_check = int(kodi.get_setting('last_list_check'))
        except: last_check = 0
        now = int(time.time())
        list_url = kodi.get_setting('scraper_url')
        scraper_password = kodi.get_setting('scraper_password')
        list_path = os.path.join(kodi.translate_path(kodi.get_profile()), 'scraper_list.txt')
        exists = os.path.exists(list_path)
        if list_url and scraper_password and (not exists or last_check < (now - (24 * 60 * 60))):
            scraper_list = utils2.get_and_decrypt(list_url, scraper_password)
            if scraper_list:
                try:
                    with open(list_path, 'w') as f:
                        f.write(scraper_list)
    
                    kodi.set_setting('last_list_check', str(now))
                    kodi.set_setting('scraper_last_update', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)))
                    for line in scraper_list.split('\n'):
                        line = line.replace(' ', '')
                        if line:
                            scraper_url, filename = line.split(',')
                            if scraper_url.startswith('http'):
                                update_scraper(filename, scraper_url)
                except Exception as e:
                    log_utils.log('Exception during scraper update: %s' % (e), log_utils.LOGWARNING)
    
def update_scraper(filename, scraper_url):
    try:
        if not filename: return
        py_path = os.path.join(kodi.get_path(), 'scrapers', filename)
        exists = os.path.exists(py_path)
        scraper_password = kodi.get_setting('scraper_password')
        if scraper_url and scraper_password:
            new_py = utils2.get_and_decrypt(scraper_url, scraper_password)
            if new_py:
                if exists:
                    with open(py_path, 'r') as f:
                        old_py = f.read()
                else:
                    old_py = ''
                
                log_utils.log('%s path: %s, new_py: %s, match: %s' % (filename, py_path, bool(new_py), new_py == old_py), log_utils.LOGDEBUG)
                if old_py != new_py:
                    with open(py_path, 'w') as f:
                        f.write(new_py)
                        
    except Exception as e:
        log_utils.log('Failure during %s scraper update: %s' % (filename, e), log_utils.LOGWARNING)

update_settings()
update_all_scrapers()
