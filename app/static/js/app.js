fetch("/api/health")
  .then((res) => res.json())
  .then((data) => {
    document.getElementById("status").textContent = "API status: " + data.status;
  })
  .catch(() => {
    document.getElementById("status").textContent = "API not reachable";
  });