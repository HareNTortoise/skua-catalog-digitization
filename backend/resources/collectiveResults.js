var express = require('express');
require('dotenv').config();

const { GoogleGenerativeAI } = require("@google/generative-ai");
var router = express.Router();
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);



module.exports = router;