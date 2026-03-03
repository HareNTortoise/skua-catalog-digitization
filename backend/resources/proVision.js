var express = require("express");
require("dotenv").config();
var get_image = require("../middleware/proVisionMiddleware");
var corsMiddleware = require("../middleware/cors");

const { GoogleGenerativeAI } = require("@google/generative-ai");
var router = express.Router();
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

router.options("/", corsMiddleware);
router.post("/", corsMiddleware, async (req, res) => {
  try {
    const img = req.body.image;
    const result = await get_image(img);
    res.json(result);
  } catch (error) {
    console.log(error);
    res.status(500).send(`Internal Server Error: ${error}`);
  }
});
module.exports = router;
