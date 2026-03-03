var express = require("express");
var router = express.Router();
var corsMiddleware = require("../middleware/cors");

/* GET home page. */
router.options("/", corsMiddleware);
router.get("/", corsMiddleware, function (req, res, next) {
  try {
    return res.json({ msg: "Hello World from Shelfie" });
  } catch (err) {
    console.log(err);
    return res.status(500).send("Server Error");
  }
});

module.exports = router;
