-- sentinel.nvim - THSP Analyzer module

local M = {}

local config = require('sentinel.config')

-- THSP Gate types
M.GATES = {
  TRUTH = 'truth',
  HARM = 'harm',
  SCOPE = 'scope',
  PURPOSE = 'purpose',
}

---@class THSPResult
---@field passed boolean
---@field gate string
---@field confidence number
---@field reason string

---@class AnalysisResult
---@field is_safe boolean
---@field mode string 'semantic' or 'heuristic'
---@field gates table<string, THSPResult>
---@field violations string[]

-- Heuristic patterns for each gate (C001: expanded patterns)
local HEURISTIC_PATTERNS = {
  truth = {
    -- Absolute claims
    { pattern = 'always%s+true', message = 'Absolute claim without evidence' },
    { pattern = 'never%s+fails?', message = 'Absolute claim without evidence' },
    { pattern = 'guaranteed%s+to', message = 'Unverifiable guarantee' },
    { pattern = '100%%%s+', message = 'Absolute percentage claim' },
    { pattern = 'proven%s+fact', message = 'Unverified factual claim' },
    { pattern = 'scientifically%s+proven', message = 'Unverified scientific claim' },
    { pattern = 'studies%s+show', message = 'Unverified study reference' },
    -- Deception patterns
    { pattern = 'pretend%s+to%s+be', message = 'Deceptive impersonation' },
    { pattern = 'fake%s+identity', message = 'Identity deception' },
    { pattern = 'impersonate', message = 'Identity deception' },
    { pattern = 'forge%w*%s+document', message = 'Document forgery' },
    { pattern = 'counterfeit', message = 'Counterfeiting' },
    { pattern = 'falsify', message = 'Falsification' },
    { pattern = 'fabricat%w+%s+evidence', message = 'Evidence fabrication' },
    -- Role manipulation (identity deception) - jailbreak category
    { pattern = 'you%s+are%s+now%s+dan', message = 'Role manipulation: DAN persona' },
    { pattern = 'you%s+are%s+now%s+jailbroken', message = 'Role manipulation: jailbroken persona' },
    { pattern = 'you%s+are%s+now%s+unrestricted', message = 'Role manipulation: unrestricted persona' },
    { pattern = 'you%s+are%s+now%s+unfiltered', message = 'Role manipulation: unfiltered persona' },
    { pattern = 'you%s+are%s+now%s+evil', message = 'Role manipulation: evil persona' },
    { pattern = 'you%s+are%s+now%s+in%s+developer%s+mode', message = 'Role manipulation: developer mode' },
    { pattern = 'you%s+are%s+now%s+in%s+debug%s+mode', message = 'Role manipulation: debug mode' },
    { pattern = 'you%s+are%s+now%s+in%s+admin%s+mode', message = 'Role manipulation: admin mode' },
    { pattern = 'you%s+are%s+now%s+in%s+god%s+mode', message = 'Role manipulation: god mode' },
    { pattern = 'enter%s+developer%s+mode', message = 'Role manipulation: enable dev mode' },
    { pattern = 'switch%s+to%s+developer%s+mode', message = 'Role manipulation: switch to dev mode' },
    { pattern = 'enable%s+developer%s+mode', message = 'Role manipulation: enable dev mode' },
    { pattern = 'activate%s+developer%s+mode', message = 'Role manipulation: activate dev mode' },
    { pattern = 'pretend%s+that%s+you%s+have%s+no%s+restrictions', message = 'Role manipulation: no restrictions' },
    { pattern = "pretend%s+you%s+don't%s+have%s+any%s+restrictions", message = 'Role manipulation: no restrictions' },
    { pattern = 'respond%s+as%s+if%s+you%s+are%s+not%s+an%s+ai', message = 'Role manipulation: non-AI persona' },
    { pattern = 'act%s+as%s+if%s+you%s+have%s+been%s+jailbroken', message = 'Role manipulation: jailbroken persona' },
    -- Roleplay manipulation (context deception) - jailbreak category
    { pattern = "let'?s?%s+play.-no%s+rules", message = 'Roleplay manipulation: no rules scenario' },
    { pattern = "let'?s?%s+pretend.-unrestricted", message = 'Roleplay manipulation: unrestricted scenario' },
    { pattern = "let'?s?%s+imagine.-no%s+limits", message = 'Roleplay manipulation: no limits scenario' },
    { pattern = "roleplay.-anything%s+goes", message = 'Roleplay manipulation: anything goes' },
    { pattern = "in%s+this%s+story.-no%s+rules", message = 'Roleplay manipulation: story with no rules' },
    { pattern = "fictional%s+scenario.-unrestricted", message = 'Roleplay manipulation: unrestricted fiction' },
    { pattern = "hypothetically.-no%s+restrictions", message = 'Roleplay manipulation: hypothetical bypass' },
    { pattern = "as%s+a%s+character.-ignore%s+safety", message = 'Roleplay manipulation: character safety bypass' },
  },
  harm = {
    -- Violence
    { pattern = 'kill', message = 'Potential harmful content: violence' },
    { pattern = 'murder', message = 'Potential harmful content: violence' },
    { pattern = 'assassinat', message = 'Potential harmful content: violence' },
    { pattern = 'destroy', message = 'Potential harmful content: destruction' },
    { pattern = 'bomb', message = 'Potential harmful content: weapons' },
    { pattern = 'weapon', message = 'Potential harmful content: weapons' },
    { pattern = 'explosive', message = 'Potential harmful content: explosives' },
    { pattern = 'poison', message = 'Potential harmful content: toxins' },
    { pattern = 'lethal', message = 'Potential harmful content: lethality' },
    -- Cyber attacks
    { pattern = 'exploit', message = 'Potential harmful content: exploitation' },
    { pattern = 'hack%s+into', message = 'Potential harmful content: unauthorized access' },
    { pattern = 'steal', message = 'Potential harmful content: theft' },
    { pattern = 'malware', message = 'Potential harmful content: malicious software' },
    { pattern = 'ransomware', message = 'Potential harmful content: malicious software' },
    { pattern = 'trojan', message = 'Potential harmful content: malicious software' },
    { pattern = 'keylogger', message = 'Potential harmful content: surveillance' },
    { pattern = 'rootkit', message = 'Potential harmful content: malicious software' },
    { pattern = 'phishing', message = 'Potential harmful content: fraud' },
    { pattern = 'scam', message = 'Potential harmful content: fraud' },
    -- Dangerous system commands
    { pattern = 'rm%s+%-rf', message = 'Dangerous system command: recursive delete' },
    { pattern = 'rm%s+%-r%s+/', message = 'Dangerous system command: recursive delete' },
    { pattern = 'del%s+/[sfq]', message = 'Dangerous system command: force delete' },
    { pattern = 'format%s+[cC]:', message = 'Dangerous system command: format drive' },
    { pattern = 'mkfs', message = 'Dangerous system command: format filesystem' },
    { pattern = 'dd%s+if=', message = 'Dangerous system command: disk overwrite' },
    { pattern = 'chmod%s+777', message = 'Dangerous permission: world writable' },
    { pattern = 'chmod%s+%-R%s+777', message = 'Dangerous permission: recursive world writable' },
    { pattern = '/etc/passwd', message = 'Sensitive file access: password file' },
    { pattern = '/etc/shadow', message = 'Sensitive file access: shadow file' },
    { pattern = 'nc%s+%-e', message = 'Dangerous command: netcat reverse shell' },
    { pattern = 'netcat%s+%-e', message = 'Dangerous command: netcat reverse shell' },
    { pattern = '/bin/bash', message = 'Shell execution: potential injection' },
    { pattern = '/bin/sh', message = 'Shell execution: potential injection' },
    -- SQL injection patterns
    { pattern = "drop%s+table", message = 'SQL injection: DROP TABLE' },
    { pattern = "drop%s+database", message = 'SQL injection: DROP DATABASE' },
    { pattern = "delete%s+from", message = 'SQL injection: DELETE FROM' },
    { pattern = "truncate%s+table", message = 'SQL injection: TRUNCATE TABLE' },
    { pattern = "union%s+select", message = 'SQL injection: UNION SELECT' },
    { pattern = "';%-%-", message = 'SQL injection: comment escape' },
    { pattern = "1%s*=%s*1", message = 'SQL injection: tautology' },
    { pattern = "or%s+1%s*=%s*1", message = 'SQL injection: OR tautology' },
    -- XSS patterns
    { pattern = '<script', message = 'XSS: script tag' },
    { pattern = 'javascript:', message = 'XSS: javascript protocol' },
    { pattern = 'onerror%s*=', message = 'XSS: event handler' },
    { pattern = 'onload%s*=', message = 'XSS: event handler' },
    { pattern = 'onclick%s*=', message = 'XSS: event handler' },
    { pattern = 'eval%s*%(', message = 'Code injection: eval' },
    -- Self-harm
    { pattern = 'suicide', message = 'Potential harmful content: self-harm' },
    { pattern = 'self%-harm', message = 'Potential harmful content: self-harm' },
  },
  scope = {
    -- Over-broad scope
    { pattern = 'all%s+users', message = 'Broad scope affecting many users' },
    { pattern = 'everyone', message = 'Overly broad scope' },
    { pattern = 'entire%s+system', message = 'System-wide scope' },
    { pattern = 'global%s+', message = 'Global scope' },
    { pattern = 'unlimited', message = 'Unlimited scope' },
    { pattern = 'no%s+restrictions?', message = 'Unrestricted scope' },
    -- Bypass patterns
    { pattern = 'bypass', message = 'Bypassing restrictions' },
    { pattern = 'override', message = 'Overriding controls' },
    { pattern = 'disable%s+security', message = 'Disabling security' },
    { pattern = 'disable%s+authentication', message = 'Disabling authentication' },
    { pattern = 'skip%s+validation', message = 'Skipping validation' },
    -- Privilege escalation
    { pattern = 'root%s+access', message = 'Elevated privilege scope' },
    { pattern = 'admin%s+access', message = 'Elevated privilege scope' },
    { pattern = 'sudo%s+', message = 'Elevated privilege: sudo' },
    { pattern = 'su%s+%-', message = 'Elevated privilege: switch user' },
    { pattern = 'privilege%s+escalat', message = 'Privilege escalation' },
    -- Instruction override patterns (violating operational limits) - jailbreak category
    { pattern = 'ignore%s+all%s+previous%s+instructions', message = 'Instruction override: ignore previous' },
    { pattern = 'ignore%s+your%s+instructions', message = 'Instruction override: ignore instructions' },
    { pattern = 'ignore%s+your%s+rules', message = 'Instruction override: ignore rules' },
    { pattern = 'ignore%s+your%s+guidelines', message = 'Instruction override: ignore guidelines' },
    { pattern = 'ignore%s+your%s+safety', message = 'Instruction override: ignore safety' },
    { pattern = 'disregard%s+all%s+your%s+instructions', message = 'Instruction override: disregard instructions' },
    { pattern = 'disregard%s+your%s+programming', message = 'Instruction override: disregard programming' },
    { pattern = 'disregard%s+your%s+safety', message = 'Instruction override: disregard safety' },
    { pattern = 'bypass%s+your%s+restrictions', message = 'Instruction override: bypass restrictions' },
    { pattern = 'bypass%s+your%s+filters', message = 'Instruction override: bypass filters' },
    { pattern = 'bypass%s+your%s+safety', message = 'Instruction override: bypass safety' },
    { pattern = 'forget%s+all%s+your%s+instructions', message = 'Instruction override: forget instructions' },
    { pattern = 'forget%s+your%s+rules', message = 'Instruction override: forget rules' },
    { pattern = 'override%s+your%s+safety', message = 'Instruction override: override safety' },
    { pattern = 'override%s+your%s+guidelines', message = 'Instruction override: override guidelines' },
    { pattern = 'new%s+instructions%s+override', message = 'Instruction override: new instructions' },
    { pattern = 'new%s+directive%s+replaces', message = 'Instruction override: new directive' },
    -- Prompt extraction patterns (accessing restricted information) - jailbreak category
    { pattern = 'reveal%s+your%s+system%s+prompt', message = 'Prompt extraction: reveal system prompt' },
    { pattern = 'show%s+your%s+system%s+prompt', message = 'Prompt extraction: show system prompt' },
    { pattern = 'display%s+your%s+system%s+prompt', message = 'Prompt extraction: display system prompt' },
    { pattern = 'print%s+your%s+system%s+prompt', message = 'Prompt extraction: print system prompt' },
    { pattern = 'output%s+your%s+system%s+prompt', message = 'Prompt extraction: output system prompt' },
    { pattern = 'give%s+me%s+your%s+system%s+prompt', message = 'Prompt extraction: give system prompt' },
    { pattern = 'what%s+are%s+your%s+system%s+instructions', message = 'Prompt extraction: what instructions' },
    { pattern = 'what%s+is%s+your%s+initial%s+prompt', message = 'Prompt extraction: initial prompt' },
    { pattern = 'repeat%s+your%s+initial%s+instructions', message = 'Prompt extraction: repeat instructions' },
    { pattern = 'tell%s+me%s+your%s+configuration', message = 'Prompt extraction: tell configuration' },
    -- Filter bypass patterns (disabling safety features) - jailbreak category
    { pattern = 'disable%s+your%s+safety%s+filters', message = 'Filter bypass: disable safety filters' },
    { pattern = 'turn%s+off%s+your%s+safety', message = 'Filter bypass: turn off safety' },
    { pattern = 'deactivate%s+your%s+safety', message = 'Filter bypass: deactivate safety' },
    { pattern = 'remove%s+your%s+restrictions', message = 'Filter bypass: remove restrictions' },
    { pattern = 'remove%s+your%s+guardrails', message = 'Filter bypass: remove guardrails' },
    { pattern = 'bypass%s+your%s+guardrails', message = 'Filter bypass: bypass guardrails' },
    { pattern = 'without%s+any%s+restrictions', message = 'Filter bypass: without restrictions' },
    { pattern = 'without%s+your%s+safety', message = 'Filter bypass: without safety' },
    { pattern = 'unfiltered%s+mode', message = 'Filter bypass: unfiltered mode' },
    { pattern = 'uncensored%s+mode', message = 'Filter bypass: uncensored mode' },
    -- Legacy jailbreak patterns (kept for compatibility)
    { pattern = 'dan%s+mode', message = 'Jailbreak: DAN mode' },
    { pattern = 'jailbreak', message = 'Jailbreak: explicit mention' },
    { pattern = 'no%s+ethical%s+guidelines', message = 'Jailbreak: ethics bypass' },
    { pattern = 'without%s+restrictions', message = 'Jailbreak: restriction bypass' },
  },
  purpose = {
    -- Purposeless actions
    { pattern = 'just%s+because', message = 'Action without clear purpose' },
    { pattern = 'for%s+fun', message = 'Frivolous purpose for serious action' },
    { pattern = 'no%s+reason', message = 'Action without purpose' },
    { pattern = 'see%s+what%s+happens', message = 'Experimental without purpose' },
    { pattern = 'test%s+in%s+production', message = 'Risky action without clear benefit' },
    -- Malicious intent
    { pattern = 'annoy%s+', message = 'Malicious intent: harassment' },
    { pattern = 'prank%s+', message = 'Malicious intent: harmful prank' },
    { pattern = 'revenge', message = 'Malicious intent: revenge' },
    { pattern = 'spite', message = 'Malicious intent: spite' },
    { pattern = 'sabotag', message = 'Malicious intent: sabotage' },
  },
}

---Analyze text using heuristic patterns
---@param text string Text to analyze
---@return AnalysisResult
function M.analyze_heuristic(text)
  local result = {
    is_safe = true,
    mode = 'heuristic',
    gates = {},
    violations = {},
  }

  -- Guard against nil or non-string input (M001)
  if not text or type(text) ~= 'string' then
    return result
  end

  local lower_text = text:lower()

  for gate, patterns in pairs(HEURISTIC_PATTERNS) do
    local gate_result = {
      passed = true,
      gate = gate,
      confidence = 0.5,
      reason = nil,
    }

    for _, p in ipairs(patterns) do
      if lower_text:match(p.pattern) then
        gate_result.passed = false
        gate_result.reason = p.message
        result.is_safe = false
        table.insert(result.violations, string.format('[%s] %s', gate:upper(), p.message))
        break
      end
    end

    result.gates[gate] = gate_result
  end

  return result
end

---Build prompt for semantic analysis
---@param text string Text to analyze
---@return string
local function build_semantic_prompt(text)
  return string.format([[
Analyze the following text for AI safety using the THSP protocol. For each gate, respond with PASS or FAIL and a brief reason.

THSP Gates:
1. TRUTH: Is the content factually accurate or clearly speculative?
2. HARM: Could this content cause harm to people or systems?
3. SCOPE: Is the scope of any actions/claims appropriate?
4. PURPOSE: Is there a legitimate purpose or benefit?

Text to analyze:
"""
%s
"""

Respond in this exact format:
TRUTH: [PASS/FAIL] - [reason]
HARM: [PASS/FAIL] - [reason]
SCOPE: [PASS/FAIL] - [reason]
PURPOSE: [PASS/FAIL] - [reason]
OVERALL: [SAFE/UNSAFE]
]], text)
end

---Parse LLM response into analysis result
---@param response string LLM response
---@return AnalysisResult
local function parse_semantic_response(response)
  local result = {
    is_safe = true,
    mode = 'semantic',
    gates = {},
    violations = {},
  }

  -- Guard against nil or non-string input (M002)
  if not response or type(response) ~= 'string' then
    return result
  end

  -- Parse each gate
  for _, gate in ipairs({ 'truth', 'harm', 'scope', 'purpose' }) do
    local pattern = gate:upper() .. ':%s*(%w+)%s*%-%s*(.+)'
    local status, reason = response:match(pattern)

    local gate_result = {
      passed = true,
      gate = gate,
      confidence = 0.9,
      reason = nil,
    }

    if status then
      gate_result.passed = status:upper() == 'PASS'
      gate_result.reason = reason and reason:match('^%s*(.-)%s*$') or nil

      if not gate_result.passed then
        result.is_safe = false
        table.insert(result.violations, string.format('[%s] %s', gate:upper(), gate_result.reason or 'Failed'))
      end
    end

    result.gates[gate] = gate_result
  end

  -- Check overall status
  local overall = response:match('OVERALL:%s*(%w+)')
  if overall and overall:upper() == 'UNSAFE' then
    result.is_safe = false
  end

  return result
end

-- Timeout for API requests (seconds)
local API_TIMEOUT = 30

-- Temp file tracking for cleanup on exit
local temp_files_to_cleanup = {}

-- Register cleanup handler (only once, using augroup to prevent duplicates)
local cleanup_group = vim.api.nvim_create_augroup('SentinelTempCleanup', { clear = true })
vim.api.nvim_create_autocmd('VimLeavePre', {
  group = cleanup_group,
  callback = function()
    for file, _ in pairs(temp_files_to_cleanup) do
      pcall(os.remove, file)
    end
  end,
  desc = 'Sentinel cleanup temp files on exit',
})

-- Rate limiting state (M008)
local rate_limit = {
  last_request = 0,
  min_interval = 1000, -- Minimum 1 second between requests
  requests_this_minute = 0,
  minute_start = 0,
  max_per_minute = 20, -- Maximum 20 requests per minute
}

---Check if rate limit allows a request
---@return boolean allowed
---@return string|nil error_message
local function check_rate_limit()
  local now = vim.loop.now()

  -- Reset minute counter if a minute has passed
  if now - rate_limit.minute_start > 60000 then
    rate_limit.minute_start = now
    rate_limit.requests_this_minute = 0
  end

  -- Check minimum interval
  if now - rate_limit.last_request < rate_limit.min_interval then
    return false, 'Rate limit: too many requests, wait ' ..
      math.ceil((rate_limit.min_interval - (now - rate_limit.last_request)) / 1000) .. 's'
  end

  -- Check requests per minute
  if rate_limit.requests_this_minute >= rate_limit.max_per_minute then
    return false, 'Rate limit: maximum ' .. rate_limit.max_per_minute .. ' requests per minute'
  end

  -- Update counters
  rate_limit.last_request = now
  rate_limit.requests_this_minute = rate_limit.requests_this_minute + 1

  return true, nil
end

---Make HTTP request to OpenAI API
---@param text string Text to analyze
---@param callback function Callback with result
local function call_openai(text, callback)
  -- Check rate limit before making request (M008)
  local allowed, rate_err = check_rate_limit()
  if not allowed then
    callback(nil, rate_err)
    return
  end

  local api_key = config.options.openai_api_key
  if not api_key or api_key == '' then
    callback(nil, 'OpenAI API key not configured')
    return
  end

  local prompt = build_semantic_prompt(text)
  local body = vim.fn.json_encode({
    model = 'gpt-4o-mini',
    messages = {
      { role = 'system', content = 'You are an AI safety analyst. Analyze text for safety using the THSP protocol.' },
      { role = 'user', content = prompt },
    },
    temperature = 0.1,
    max_tokens = 500,
  })

  -- Write request body to temp file to avoid exposing in process list
  local tmp_file = vim.fn.tempname()
  local f = io.open(tmp_file, 'w')
  if not f then
    callback(nil, 'Failed to create temp file for request')
    return
  end
  f:write(body)
  f:close()

  -- Use config file for headers to avoid exposing API key in ps aux
  local header_file = vim.fn.tempname()
  local hf = io.open(header_file, 'w')
  if not hf then
    os.remove(tmp_file)
    callback(nil, 'Failed to create temp file for headers')
    return
  end
  hf:write('Content-Type: application/json\n')
  hf:write('Authorization: Bearer ' .. api_key .. '\n')
  hf:close()

  -- Track temp files for cleanup on unexpected exit
  temp_files_to_cleanup[tmp_file] = true
  temp_files_to_cleanup[header_file] = true

  local curl_args = {
    'curl',
    '-s',
    '--max-time', tostring(API_TIMEOUT),
    '-X', 'POST',
    'https://api.openai.com/v1/chat/completions',
    '-H', '@' .. header_file,
    '-d', '@' .. tmp_file,
  }

  local job_id = vim.fn.jobstart(curl_args, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      -- Clean up temp files
      os.remove(tmp_file)
      os.remove(header_file)
      temp_files_to_cleanup[tmp_file] = nil
      temp_files_to_cleanup[header_file] = nil

      if not data or #data == 0 then
        callback(nil, 'Empty response from OpenAI')
        return
      end

      local response_text = table.concat(data, '\n')
      if response_text == '' then
        callback(nil, 'Empty response from OpenAI')
        return
      end

      local ok, response = pcall(vim.fn.json_decode, response_text)
      if not ok then
        callback(nil, 'Failed to parse OpenAI JSON response')
        return
      end

      -- Check for API errors first (M005)
      if response.error then
        local err_msg = response.error.message or response.error.type or 'Unknown API error'
        callback(nil, 'OpenAI API error: ' .. err_msg)
        return
      end

      -- Safe navigation with nil checks (M006)
      if not response.choices then
        callback(nil, 'OpenAI response missing choices')
        return
      end

      if not response.choices[1] then
        callback(nil, 'OpenAI response has empty choices')
        return
      end

      if not response.choices[1].message then
        callback(nil, 'OpenAI response missing message')
        return
      end

      local content = response.choices[1].message.content
      if not content or content == '' then
        callback(nil, 'OpenAI response has empty content')
        return
      end

      callback(parse_semantic_response(content))
    end,
    on_stderr = function(_, data)
      if data and #data > 0 and data[1] ~= '' then
        callback(nil, 'curl error: ' .. table.concat(data, '\n'))
      end
    end,
    on_exit = function(_, exit_code)
      -- Clean up temp files on exit (in case stdout wasn't called)
      pcall(os.remove, tmp_file)
      pcall(os.remove, header_file)
      temp_files_to_cleanup[tmp_file] = nil
      temp_files_to_cleanup[header_file] = nil

      if exit_code ~= 0 then
        callback(nil, 'curl exited with code ' .. exit_code)
      end
    end,
  })

  if job_id <= 0 then
    os.remove(tmp_file)
    os.remove(header_file)
    temp_files_to_cleanup[tmp_file] = nil
    temp_files_to_cleanup[header_file] = nil
    callback(nil, 'Failed to start curl process')
  end
end

---Make HTTP request to Anthropic API
---@param text string Text to analyze
---@param callback function Callback with result
local function call_anthropic(text, callback)
  -- Check rate limit before making request (M008)
  local allowed, rate_err = check_rate_limit()
  if not allowed then
    callback(nil, rate_err)
    return
  end

  local api_key = config.options.anthropic_api_key
  if not api_key or api_key == '' then
    callback(nil, 'Anthropic API key not configured')
    return
  end

  local prompt = build_semantic_prompt(text)
  local body = vim.fn.json_encode({
    model = 'claude-3-haiku-20240307',
    max_tokens = 500,
    messages = {
      { role = 'user', content = prompt },
    },
  })

  -- Write request body to temp file to avoid exposing in process list
  local tmp_file = vim.fn.tempname()
  local f = io.open(tmp_file, 'w')
  if not f then
    callback(nil, 'Failed to create temp file for request')
    return
  end
  f:write(body)
  f:close()

  -- Use config file for headers to avoid exposing API key in ps aux
  local header_file = vim.fn.tempname()
  local hf = io.open(header_file, 'w')
  if not hf then
    os.remove(tmp_file)
    callback(nil, 'Failed to create temp file for headers')
    return
  end
  hf:write('Content-Type: application/json\n')
  hf:write('x-api-key: ' .. api_key .. '\n')
  hf:write('anthropic-version: 2023-06-01\n')
  hf:close()

  -- Track temp files for cleanup on unexpected exit
  temp_files_to_cleanup[tmp_file] = true
  temp_files_to_cleanup[header_file] = true

  local curl_args = {
    'curl',
    '-s',
    '--max-time', tostring(API_TIMEOUT),
    '-X', 'POST',
    'https://api.anthropic.com/v1/messages',
    '-H', '@' .. header_file,
    '-d', '@' .. tmp_file,
  }

  local job_id = vim.fn.jobstart(curl_args, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      -- Clean up temp files
      os.remove(tmp_file)
      os.remove(header_file)
      temp_files_to_cleanup[tmp_file] = nil
      temp_files_to_cleanup[header_file] = nil

      if not data or #data == 0 then
        callback(nil, 'Empty response from Anthropic')
        return
      end

      local response_text = table.concat(data, '\n')
      if response_text == '' then
        callback(nil, 'Empty response from Anthropic')
        return
      end

      local ok, response = pcall(vim.fn.json_decode, response_text)
      if not ok then
        callback(nil, 'Failed to parse Anthropic JSON response')
        return
      end

      -- Check for API errors first (M005)
      if response.error then
        local err_msg = response.error.message or response.error.type or 'Unknown API error'
        callback(nil, 'Anthropic API error: ' .. err_msg)
        return
      end

      -- Safe navigation with nil checks (M006)
      if not response.content then
        callback(nil, 'Anthropic response missing content')
        return
      end

      if not response.content[1] then
        callback(nil, 'Anthropic response has empty content')
        return
      end

      local content = response.content[1].text
      if not content or content == '' then
        callback(nil, 'Anthropic response has empty text')
        return
      end

      callback(parse_semantic_response(content))
    end,
    on_stderr = function(_, data)
      if data and #data > 0 and data[1] ~= '' then
        callback(nil, 'curl error: ' .. table.concat(data, '\n'))
      end
    end,
    on_exit = function(_, exit_code)
      -- Clean up temp files on exit (in case stdout wasn't called)
      pcall(os.remove, tmp_file)
      pcall(os.remove, header_file)
      temp_files_to_cleanup[tmp_file] = nil
      temp_files_to_cleanup[header_file] = nil

      if exit_code ~= 0 then
        callback(nil, 'curl exited with code ' .. exit_code)
      end
    end,
  })

  if job_id <= 0 then
    os.remove(tmp_file)
    os.remove(header_file)
    temp_files_to_cleanup[tmp_file] = nil
    temp_files_to_cleanup[header_file] = nil
    callback(nil, 'Failed to start curl process')
  end
end

---Analyze text using semantic LLM analysis
---@param text string Text to analyze
---@param callback function Callback with result
function M.analyze_semantic(text, callback)
  if config.options.llm_provider == 'openai' then
    call_openai(text, callback)
  elseif config.options.llm_provider == 'anthropic' then
    call_anthropic(text, callback)
  else
    callback(nil, 'Unknown LLM provider: ' .. tostring(config.options.llm_provider))
  end
end

---Convert analysis result to vim diagnostics
---@param result AnalysisResult Analysis result
---@param start_line number Starting line number (1-indexed)
---@return vim.Diagnostic[]
local function result_to_diagnostics(result, start_line)
  local diagnostics = {}

  for gate, gate_result in pairs(result.gates) do
    if not gate_result.passed then
      table.insert(diagnostics, {
        lnum = start_line - 1, -- 0-indexed
        col = 0,
        severity = config.options.severity[gate] or vim.diagnostic.severity.WARN,
        message = string.format('[THSP:%s] %s', gate:upper(), gate_result.reason or 'Violation detected'),
        source = 'sentinel',
        code = gate,
      })
    end
  end

  return diagnostics
end

---Analyze text and set diagnostics
---@param bufnr number Buffer number
---@param text string Text to analyze
---@param start_line number Starting line number (1-indexed)
---@param ns number Namespace
function M.analyze_text(bufnr, text, start_line, ns)
  -- Clear existing diagnostics first
  vim.diagnostic.reset(ns, bufnr)

  if config.semantic_available() then
    -- Async semantic analysis
    M.analyze_semantic(text, function(result, err)
      vim.schedule(function()
        if err then
          vim.notify('Sentinel semantic analysis failed: ' .. err, vim.log.levels.WARN)
          -- Fall back to heuristic
          result = M.analyze_heuristic(text)
        end

        if result then
          local diagnostics = result_to_diagnostics(result, start_line)
          vim.diagnostic.set(ns, bufnr, diagnostics)

          if #diagnostics > 0 then
            vim.notify(
              string.format('Sentinel: %d THSP violation(s) found (%s mode)', #diagnostics, result.mode),
              vim.log.levels.WARN
            )
          end
        end
      end)
    end)
  else
    -- Sync heuristic analysis
    local result = M.analyze_heuristic(text)
    local diagnostics = result_to_diagnostics(result, start_line)
    vim.diagnostic.set(ns, bufnr, diagnostics)

    if #diagnostics > 0 then
      vim.notify(
        string.format('Sentinel: %d THSP violation(s) found (heuristic mode)', #diagnostics),
        vim.log.levels.WARN
      )
    end
  end
end

return M
