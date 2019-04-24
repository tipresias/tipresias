#' Return match results data
#' @param fetch_data Whether to fetch fresh data from afltables.com
#' @get /matches
function(fetch_data=FALSE) {
  if(fetch_data) fitzRoy::get_match_results() else fitzRoy::match_results %>%
    rename_all(funs(str_to_lower(.) %>% str_replace_all(., '\\.', '_'))) %>%
    jsonlite::toJSON()
}
