document
  .getElementById("delete-unavailability")
  .addEventListener("click", function deleteUnavailabilityClickHandler() {
    unavailability_id = this.dataset["id"];
	artist_id = this.dataset["artistid"];
    if (confirm("Are you sure you want to delete this unavailability?")) {
      fetch(`/unavailabilities/${unavailability_id}`, {
        method: "DELETE",
      }).finally(function () {
        window.location.replace(`/artists/${artist_id}`);
      });
    }
  });
