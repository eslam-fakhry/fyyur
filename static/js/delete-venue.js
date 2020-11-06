document
  .getElementById("delete-venue")
  .addEventListener("click", function deleteVenueClickHandler() {
    venue_id = this.getAttribute("data-id");
    if (confirm("Are you sure you want to delete this venue?")) {
      fetch(`/venues/${venue_id}`, {
        method: "DELETE",
      }).finally(function () {
        window.location.replace("/");
      });
    }
  });
