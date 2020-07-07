function main(splash)
  local function fill_in_predicted_margin(predicted_margin, match_element)
    local margin_input = match_element:querySelector('[name="Margin"]')

    -- There is only one Margin input. The element check is to make sure we use
    -- the correct predicted_margin value.
    if margin_input then assert(splash:select('form'):fill({Margin = predicted_margin})) end
  end

  local function element_is_predicted_winner(element, predicted_winner)
    local element_team_name = splash.args.team_translations[element:text()] or
      element:text()
    -- We use offset parent rather than visible/hidden, because Splash thinks
    -- all team elements are visible, when only the first one actually is.
    -- This raises an error when we try to click on the invisible element.
    local element_is_visible = element.offsetParent

    return element_is_visible and element_team_name == predicted_winner
  end

  local function select_predicted_winner(predicted_winner, match_element)
    local team_elements = match_element:querySelectorAll('.team-name.team-full')

    for _, team_name_element in ipairs(team_elements) do
      if element_is_predicted_winner(team_name_element, predicted_winner) then
          -- Even though it's not an input element, triggering a click
          -- on the team name still triggers the associated radio button.
          assert(team_name_element:mouse_click())
      end
    end
  end

  local function get_match_prediction(match_element)
    for team_name, _ in pairs(splash.args.predictions) do
      if string.find(match_element:text(), team_name) then
        return {team_name, splash.args.predictions[team_name]}
      end
    end

    assert(false,
          'WARNING: No matching prediction was found for a match element. ' ..
          'This likely means that the tip submission page has not ' ..
          'been updated for the next round yet. Try again tomorrow.')
  end

  local function get_match_elements()
    local prediction_count = 0
    for _, _ in pairs(splash.args.predictions) do
      prediction_count = prediction_count + 1
    end

    local match_elements = splash:select_all('.tipping-container')
    assert(#match_elements == prediction_count,
          'Match count (' .. #match_elements .. ') does not equal prediction ' ..
          'count (' .. prediction_count .. ').')

    return match_elements
  end

  local function fill_in_tipping_form()
    for _, match_element in ipairs(get_match_elements()) do
      local predictions = get_match_prediction(match_element)

      select_predicted_winner(predictions[1], match_element)
      fill_in_predicted_margin(predictions[2], match_element)
    end
  end

  local function log_in(url)
    -- Have to use second login form, because the first is some
    -- invisible Angular something something
    local form = splash:select_all('[name=\"frmLogin\"]')[2]
    local form_inputs = {
      userLogin = splash.args.username,
      userPassword = splash.args.password,
    }

    assert(form:fill(form_inputs))
    assert(form:submit())
    splash:wait(2.0)

    assert(string.find(splash:html(), 'Welcome to ESPNfootytips') == nil,
          'Either the username or password was incorrect, ' ..
          'and we failed to log in.')
    assert(string.find(splash:url(), url),
          'On wrong URL: ' .. splash:url() .. 'Expected: ' .. url)
  end

  local url = splash.args.url
  assert(splash:go(url))
  splash:wait(1.0)

  log_in(url)
  fill_in_tipping_form()

  -- Need to click button instead of submitting form directly,
  -- because we need to trigger some javascript nonsense for the form
  -- to actually get submitted
  local submit_btn = splash:select('.tipform-submit-button')
  assert(submit_btn:mouse_click())
  splash:wait(1.0)

  local success_page = "https://www.footytips.com.au/tipping/afl/tipspost"
  assert(string.find(splash:url(), success_page),
        "Wasn't redirected to success page after submitting tips. Current URL is: " ..
        splash:url())
end