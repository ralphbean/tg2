# -*- coding: utf-8 -*-

import os
from tg.test_stack import TestConfig
from webtest import TestApp
from nose.tools import eq_


def setup_noDB():
    global_config = {'debug': 'true', 
                     'error_email_from': 'paste@localhost', 
                     'smtp_server': 'localhost'}
    
    base_config = TestConfig(folder = 'dispatch', 
                             values = {'use_sqlalchemy': False}
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app

app = setup_noDB()

def test_tg_style_default():
    resp = app.get('/sdfaswdfsdfa') #random string should be caught by the default route
    assert 'Default' in resp.body

def test_url_encoded_param_passing():
    resp = app.get('/feed?feed=http%3A%2F%2Fdeanlandolt.com%2Ffeed%2Fatom%2F')
    assert "http://deanlandolt.com/feed/atom/" in resp.body

def test_tg_style_index():
    resp = app.get('/index/')
    print resp
    assert 'hello' in resp.body

def test_tg_style_subcontroller_index():
    resp = app.get('/sub/index')
    assert "sub index" in resp.body

def test_tg_style_subcontroller_default():
    resp=app.get('/sub/bob/tim/joe')
    assert "bob" in resp.body
    assert 'tim' in resp.body
    assert 'joe' in resp.body

def test_redirect_absolute():
    resp = app.get('/redirect_me?target=/')
    print resp.status
    assert resp.status == "302 Found", resp.status
    assert 'http://localhost/' in resp.headers['location']
    print resp
    resp = resp.follow()
    print resp
    assert 'hello world' in resp

def test_redirect_relative():
    resp = app.get('/redirect_me?target=hello&name=abc')
    print resp
    resp = resp.follow()
    assert'Hello abc' in resp
    resp = app.get('/sub/redirect_me?target=hello&name=def')
    print resp
    resp = resp.follow()
    print resp
    assert'Why HELLO! def' in resp
    resp = app.get('/sub/redirect_me?target=../hello&name=ghi')
    print resp
    resp = resp.follow()
    print resp
    assert'Hello ghi' in resp

def test_redirect_external():
    resp = app.get('/redirect_me?target=http://example.com')
    print resp
    assert resp.status == "302 Found" and dict(resp.headers)['location'] == 'http://example.com'

def test_redirect_param():
    resp = app.get('/redirect_me?target=/hello&name=paj')
    resp = resp.follow()
    assert'Hello paj' in resp
    resp = app.get('/redirect_me?target=/hello&name=pbj')
    resp = resp.follow()
    assert'Hello pbj' in resp
    resp = app.get('/redirect_me?target=/hello&silly=billy&name=pcj')
    resp = resp.follow()
    print resp
    assert'Hello pcj' in resp

def test_redirect_cookie():
    resp = app.get('/redirect_cookie?name=stefanha').follow()
    assert'Hello stefanha' in resp

def test_subcontroller_redirect_subindex():
    resp=app.get('/sub/redirect_sub').follow()
    assert'sub index' in resp

def test_subcontroller_redirect_sub2index():
    resp=app.get('/sub2/').follow()
    assert'hello list' in resp

def test_subcontroller_redirect_no_slash_sub2index():
    resp=app.get('/sub2/').follow()
    assert'hello list' in resp

def test_flash_redirect():
    resp = app.get('/flash_redirect').follow()
    assert'Wow, flash!' in resp
    
def test_flash_no_redirect():
    resp = app.get('/flash_no_redirect')
    assert'Wow, flash!' in resp

def test_flash_unicode():
    resp = app.get('/flash_unicode').follow()
    content = resp.body.decode('utf8')
    assert u'Привет, мир!' in content
    
def test_flash_status():
    resp = app.get('/flash_status')
    assert'status_ok'in resp

def test_tg_format_param():
    resp = app.get('/stacked_expose/?tg_format=application/json')
    assert '{"got_json' in resp.body

def test_custom_content_type():
    resp = app.get('/custom_content_type')
    assert 'image/png' == dict(resp.headers)['content-type']
    assert resp.body == 'PNG'
    
def test_basicurls():
    resp = app.get("/test_url_sop")
