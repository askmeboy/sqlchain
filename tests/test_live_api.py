#!/usr/bin/env python
#
#   live api test - unit test module
#     - supports multiple coins by selecting the db based on cointype
#     - read api urls from livetest db and call live api
#     - compare json returned to livetest db json
#

import sys, time, requests, json

try:
    from deepdiff import DeepDiff
except ImportError:
    print "Cannot run database tests without deepdiff module"

try:
    import sqlite3 as db
except ImportError:
    print "Cannot run database tests without sqlite3 module"

import pytest

millis = lambda: int(round(time.time() * 1000))
server = None

live = pytest.mark.skipif(not pytest.config.getoption("--runlive"), reason = "need --runlive option to run")
nosigs = pytest.mark.skipif(pytest.config.getoption("--nosigs"), reason = "cannot test with nosigs db")

# livetest db created by mklivetestdb.py
@pytest.fixture(scope="module")
def testdb(request):
    global server
    if 'sqlite3' not in sys.modules:
        pytest.skip("sqlite3 module not available.")
        return None
    server = request.config.getoption("--server")
    coin = request.config.getoption("--coin")
    cwd = str(request.fspath.join('..'))
    sql = db.connect(cwd+'/livetest.%s.db' % coin,isolation_level=None)
    cur = sql.cursor()
    cur.execute("select name from sqlite_master where name='calls';")
    if cur.fetchone() is None:
        pytest.skip("livetest.%s.db not initialized." % coin)
        return None
    if not request.config.getoption("--append"):
        cur.execute("delete from tests;")
    return cur

def api_call(url):
    try:
        call_ts = millis()
        r = requests.get('http://'+server+url)
        if r.status_code == requests.codes.ok:
            return r.json(),millis()-call_ts
    except requests.exceptions.ConnectionError:
        pytest.skip("requires api connection to run")
        return { "error": "Connect Error: http://"+server+url },0
    return { "error": r.status_code },0

def api_diff(cur, sqlstr, **kwargs):
    log,diff = [],{}
    cur.execute("select url,result from calls where %s;" % sqlstr)
    for url,result in cur:
        rtn,rtt = api_call(url)
        if 'error' in rtn:
            return rtn
        diff = DeepDiff(json.loads(result), rtn, ignore_order=True, **kwargs)
        log.append((url,str(rtn),str(diff),rtt))
        if diff != {}:
            break
    cur.executemany("insert into tests (url,result,diff,rtt) values (?,?,?,?);", log )
    return diff

@live
def test_live_api_block(testdb):
    assert api_diff(testdb, "url like '/block/%'", exclude_paths={"root['confirmations']"}) == {}

@live
def test_live_api_block_index(testdb):
    assert api_diff(testdb, "url like '/block-index/%'") == {}

@live
@nosigs
def test_live_api_rawblock(testdb): # not currently supported
    assert True

@live
def test_live_api_blocks(testdb): # not currently supported
    assert True

@live
def test_live_api_tx(testdb):
    assert api_diff(testdb, "url like '/tx/%'") == {}

@live
@nosigs
def test_live_api_rawtx(testdb):
    assert api_diff(testdb, "url like '/rawtx/%'") == {}

@live
def test_live_api_addr(testdb):
    assert api_diff(testdb, "url like '/addr/%'") == {}

@live
def test_live_api_utxo(testdb):
    assert api_diff(testdb, "url like '/addr/%/utxo'") == {}

@live
def test_live_api_txs_block(testdb):
    assert api_diff(testdb, "url like '/txs/?block=%'") == {}

@live
def test_live_api_txs_addr(testdb):
    assert api_diff(testdb, "url like '/txs/?address=%'") == {}

@live
def test_live_api_addrs(testdb):
    assert api_diff(testdb, "url like '/addrs/%/utxo'") == {}

@live
def test_live_api_status(testdb):
    assert True
