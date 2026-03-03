var express = require("express");
require("dotenv").config();
var corsMiddleware = require("../../middleware/cors");
var get_multiple_image = require("../../middleware/mulipleJobsMiddleware/multipleProVisionMiddleware.js");

const { GoogleGenerativeAI } = require("@google/generative-ai");
var router = express.Router();
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

router.options("/");
router.post("/", async (req, res) => {
  try{
    var lst = [];
    const imgs = req.body.images;
    for (const img of imgs) {
      const result = await get_multiple_image(img);
      lst.push(result);
    }
    res.json(lst);
  }catch(err){
    console.log(err);
  }
});

module.exports = router;
