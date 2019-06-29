'use strict'

const path = require('path')

module.exports.env = () => (
  {
    project: process.env.PROJECT_ID,
    credentials: path.resolve(__dirname, process.env.GOOGLE_APPLICATION_CREDENTIALS),
    gcpf_token: process.env.GCPF_TOKEN,
    afl_data_service: process.env.AFL_DATA_SERVICE,
  }
)
