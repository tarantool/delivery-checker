#!/usr/bin/env tarantool

local log = require('log')
local fio = require('fio')
local json = require('json')

local function test(func)
    local _, err = pcall(func)
    if err ~= nil then
        return err
    end
    return 'OK'
end

local function write_results(results)
    local res_filename = os.getenv('RESULTS_FILE')
    if res_filename == nil then
        log.warn('No environment variable RESULTS_FILE. Name "test_results.json" will be used.')
        res_filename = 'tests_results.json'
    end
    local res_fh = fio.open(res_filename, { 'O_CREAT', 'O_TRUNC', 'O_WRONLY' }, tonumber('644', 8))
    res_fh:write(json.encode(results))
    res_fh:close()
end

local function box_cfg()
    fio.mktree('data/memtx')
    fio.mktree('data/vinyl')
    fio.mktree('data/wal')
    box.cfg({
        listen = 3301,
        memtx_dir = 'data/memtx',
        vinyl_dir = 'data/vinyl',
        wal_dir = 'data/wal',
    })
end

local function tnt_version()
    local expected_version = os.getenv('TNT_VERSION')
    local begin = string.find(_TARANTOOL, expected_version, 1, true)
    assert(begin == 1, 'Expected version: ' .. expected_version .. ', got: ' .. _TARANTOOL)
end

local results = {}
results['tnt_version'] = test(tnt_version)
results['box_cfg'] = test(box_cfg)
write_results(results)

os.exit()
