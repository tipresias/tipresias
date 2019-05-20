EARLIEST_BETTING_DATA_SEASON <- 2010

describe("fetch_betting_odds()", {
  start_date <- "2012-01-01"
  end_date <- "2013-12-31"
  year_count <- 2

  it("returns a data.frame composed of match rows", {
    betting_odds_data <- fetch_betting_odds(
      start_date = start_date, end_date = end_date
    )

    expect_equal(class(betting_odds_data), "data.frame")
    expect_gt(length(betting_odds_data), year_count)

    expect_type(betting_odds_data$date, "Date")
    expect_type(betting_odds_data$venue, "character")
    expect_type(betting_odds_data$team, "character")
    expect_type(betting_odds_data$score, "numeric")
    expect_type(betting_odds_data$margin, "numeric")
    expect_type(betting_odds_data$win_odds, "numeric")
    expect_type(betting_odds_data$win_paid, "numeric")
    expect_type(betting_odds_data$line_odds, "numeric")
    expect_type(betting_odds_data$line_paid, "numeric")
    expect_type(betting_odds_data$round, "character")
    expect_type(betting_odds_data$season, "numeric")
  })

  describe("when one of the dates is out of range of available data", {
    start_date <- "2008-01-01"
    end_date <- "2010-12-31"

    it("returns a data.frame with rows from valid date range", {
      betting_odds_data <- fetch_betting_odds(
        start_date = start_date, end_date = end_date
      )
      earliest_year <- betting_odds_data$date %>%
        purrr::map(lubridate::year) %>%
          unlist(.) %>%
          min(.)

      expect_equal(class(betting_odds_data), "data.frame")
      expect_equal(earliest_year, EARLIEST_BETTING_DATA_SEASON)
    })
  })
})
