const http = require("http");

const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ ok: true, path: req.url }));
});

const port = process.env.PORT || 3000;
server.listen(port, () => {
  console.log(`base-workspace listening on ${port}`);
});
