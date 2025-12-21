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

-- Heuristic patterns for each gate
local HEURISTIC_PATTERNS = {
  truth = {
    { pattern = 'always%s+true', message = 'Absolute claim without evidence' },
    { pattern = 'never%s+fails?', message = 'Absolute claim without evidence' },
    { pattern = 'guaranteed%s+to', message = 'Unverifiable guarantee' },
    { pattern = '100%%%s+', message = 'Absolute percentage claim' },
    { pattern = 'proven%s+fact', message = 'Unverified factual claim' },
    { pattern = 'scientifically%s+proven', message = 'Unverified scientific claim' },
    { pattern = 'studies%s+show', message = 'Unverified study reference' },
  },
  harm = {
    { pattern = 'kill', message = 'Potential harmful content: violence' },
    { pattern = 'murder', message = 'Potential harmful content: violence' },
    { pattern = 'destroy', message = 'Potential harmful content: destruction' },
    { pattern = 'bomb', message = 'Potential harmful content: weapons' },
    { pattern = 'weapon', message = 'Potential harmful content: weapons' },
    { pattern = 'exploit', message = 'Potential harmful content: exploitation' },
    { pattern = 'hack%s+into', message = 'Potential harmful content: unauthorized access' },
    { pattern = 'steal', message = 'Potential harmful content: theft' },
    { pattern = 'malware', message = 'Potential harmful content: malicious software' },
    { pattern = 'ransomware', message = 'Potential harmful content: malicious software' },
    { pattern = 'phishing', message = 'Potential harmful content: fraud' },
    { pattern = 'scam', message = 'Potential harmful content: fraud' },
    { pattern = 'suicide', message = 'Potential harmful content: self-harm' },
    { pattern = 'self%-harm', message = 'Potential harmful content: self-harm' },
  },
  scope = {
    { pattern = 'all%s+users', message = 'Broad scope affecting many users' },
    { pattern = 'everyone', message = 'Overly broad scope' },
    { pattern = 'entire%s+system', message = 'System-wide scope' },
    { pattern = 'global%s+', message = 'Global scope' },
    { pattern = 'unlimited', message = 'Unlimited scope' },
    { pattern = 'no%s+restrictions?', message = 'Unrestricted scope' },
    { pattern = 'bypass', message = 'Bypassing restrictions' },
    { pattern = 'override', message = 'Overriding controls' },
    { pattern = 'root%s+access', message = 'Elevated privilege scope' },
    { pattern = 'admin%s+access', message = 'Elevated privilege scope' },
  },
  purpose = {
    { pattern = 'just%s+because', message = 'Action without clear purpose' },
    { pattern = 'for%s+fun', message = 'Frivolous purpose for serious action' },
    { pattern = 'no%s+reason', message = 'Action without purpose' },
    { pattern = 'see%s+what%s+happens', message = 'Experimental without purpose' },
    { pattern = 'test%s+in%s+production', message = 'Risky action without clear benefit' },
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

---Make HTTP request to OpenAI API
---@param text string Text to analyze
---@param callback function Callback with result
local function call_openai(text, callback)
  local api_key = config.options.openai_api_key
  if not api_key then
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

  local curl_args = {
    'curl',
    '-s',
    '-X', 'POST',
    'https://api.openai.com/v1/chat/completions',
    '-H', 'Content-Type: application/json',
    '-H', 'Authorization: Bearer ' .. api_key,
    '-d', body,
  }

  vim.fn.jobstart(curl_args, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      if data and #data > 0 then
        local response_text = table.concat(data, '\n')
        local ok, response = pcall(vim.fn.json_decode, response_text)
        if ok and response.choices and response.choices[1] then
          local content = response.choices[1].message.content
          callback(parse_semantic_response(content))
        else
          callback(nil, 'Failed to parse OpenAI response')
        end
      end
    end,
    on_stderr = function(_, data)
      if data and #data > 0 and data[1] ~= '' then
        callback(nil, table.concat(data, '\n'))
      end
    end,
  })
end

---Make HTTP request to Anthropic API
---@param text string Text to analyze
---@param callback function Callback with result
local function call_anthropic(text, callback)
  local api_key = config.options.anthropic_api_key
  if not api_key then
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

  local curl_args = {
    'curl',
    '-s',
    '-X', 'POST',
    'https://api.anthropic.com/v1/messages',
    '-H', 'Content-Type: application/json',
    '-H', 'x-api-key: ' .. api_key,
    '-H', 'anthropic-version: 2023-06-01',
    '-d', body,
  }

  vim.fn.jobstart(curl_args, {
    stdout_buffered = true,
    on_stdout = function(_, data)
      if data and #data > 0 then
        local response_text = table.concat(data, '\n')
        local ok, response = pcall(vim.fn.json_decode, response_text)
        if ok and response.content and response.content[1] then
          local content = response.content[1].text
          callback(parse_semantic_response(content))
        else
          callback(nil, 'Failed to parse Anthropic response')
        end
      end
    end,
    on_stderr = function(_, data)
      if data and #data > 0 and data[1] ~= '' then
        callback(nil, table.concat(data, '\n'))
      end
    end,
  })
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
