describe("fetch_rosters()", {
  # Fetching data takes awhile, so we do it once for all tests
  rosters_data <- fetch_rosters(NULL)

  it("returns a data.frame", {
    expect_equal(class(rosters_data), "data.frame")
  })

  it("has the correct data type for each column", {
    expect_type(rosters_data$player_name, "character")
    expect_type(rosters_data$playing_for, "character")
    expect_type(rosters_data$home_team, "character")
    expect_type(rosters_data$away_team, "character")
    expect_type(rosters_data$date, "double")
    expect_type(rosters_data$season, "double")
    expect_type(rosters_data$match_id, "character")
  })
})
