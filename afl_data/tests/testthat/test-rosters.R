describe("fetch_rosters()", {
  # Fetching data takes awhile, so we do it once for all tests
  roster_data <- fetch_rosters(NULL)

  it("returns a data.frame", {
    expect_equal(class(roster_data), "data.frame")
  })

  it("has the correct data type for each column", {
    expect_type(roster_data$player_name, "character")
    expect_type(roster_data$playing_for, "character")
    expect_type(roster_data$home_team, "character")
    expect_type(roster_data$away_team, "character")
    expect_type(roster_data$date, "double")
    expect_type(roster_data$season, "double")
    expect_type(roster_data$match_id, "character")
  })
})
