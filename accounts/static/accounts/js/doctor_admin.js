(function () {
    "use strict";

    function getRow(fieldName) {
        const field = document.getElementById("id_" + fieldName);

        if (!field) {
            return null;
        }

        return field.closest(".form-row");
    }

    function updateDoctorFields() {
        const roleSelect = document.getElementById("id_role");

        if (!roleSelect) {
            return;
        }

        const isDoctor = roleSelect.value === "doctor";

        const doctorFields = [
            "specialization",
            "qualification",
            "experience_years",
            "consultation_fee",
            "rating",
            "is_available",
            "is_verified"
        ];

        doctorFields.forEach(function (fieldName) {
            const row = getRow(fieldName);

            if (row) {
                row.style.display = isDoctor ? "" : "none";
            }
        });
    }

    function init() {
        const roleSelect = document.getElementById("id_role");

        if (!roleSelect) {
            return;
        }

        roleSelect.addEventListener("change", updateDoctorFields);

        updateDoctorFields();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();