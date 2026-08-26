$(function () {
    initializeItemWriteForm();
    initializeItemStatusToggle();

    function initializeItemWriteForm() {
        const $form = $("#itemWriteForm");

        if ($form.length === 0) {
            return;
        }

        const $typeInputs = $('input[name="type"]');
        const $priceField = $("#priceField");
        const $priceInput = $("#itemPrice");
        const $wantedItemField = $("#wantedItemField");
        const $wantedItemInput = $("#wantedItem");
        const $acceptAnything = $("#acceptAnything");
        const $imageInput = $("#itemImage");
        const $imagePreviewFile = $("#imagePreviewFile");
        const $imagePreviewText = $("#imagePreviewText");
        const $imageError = $("#imageError");
        const $titleInput = $("#itemTitle");
        const $descriptionInput = $("#itemDescription");
        const $descriptionCount = $("#descriptionCount");
        const $submitButton = $("#itemSubmitButton");
        const allowedImageTypes = [
            "image/jpeg",
            "image/png",
            "image/webp"
        ];
        const maximumImageSize = 5 * 1024 * 1024;

        let selectedImageIsValid = false;

        function getSelectedType() {
            return $('input[name="type"]:checked').val();
        }

        function updateTypeFields() {
            const selectedType = getSelectedType();
            const isSale = selectedType === "sale";
            const isSwap = selectedType === "swap";

            $priceField.toggleClass("d-none", !isSale);
            $priceInput
                .prop("disabled", !isSale)
                .prop("required", isSale);

            $wantedItemField.toggleClass("d-none", !isSwap);
            $acceptAnything.prop("disabled", !isSwap);

            const acceptsAnything =
                $acceptAnything.is(":checked");

            $wantedItemInput
                .prop("disabled", !isSwap || acceptsAnything)
                .prop("required", isSwap && !acceptsAnything);

            updateFormValidity();
        }

        function resetImagePreview() {
            selectedImageIsValid = false;
            $imagePreviewFile
                .attr("src", "")
                .addClass("d-none");
            $imagePreviewText.removeClass("d-none");
        }

        function showImageError(message) {
            resetImagePreview();
            $imageInput.addClass("is-invalid");
            $imageError.text(message);
        }

        function updateImagePreview(file) {
            const reader = new FileReader();

            reader.onload = function (event) {
                $imagePreviewFile
                    .attr("src", event.target.result)
                    .removeClass("d-none");
                $imagePreviewText.addClass("d-none");
            };

            reader.readAsDataURL(file);
        }

        function isFormValid() {
            const titleIsValid =
                $titleInput.val().trim().length > 0;
            const descriptionIsValid =
                $descriptionInput.val().trim().length > 0;
            const selectedType = getSelectedType();

            let typeFieldsAreValid = false;

            if (selectedType === "sale") {
                typeFieldsAreValid =
                    $priceInput.val() !== "" &&
                    Number($priceInput.val()) > 0;
            }

            if (selectedType === "free") {
                typeFieldsAreValid = true;
            }

            if (selectedType === "swap") {
                typeFieldsAreValid =
                    $acceptAnything.is(":checked") ||
                    $wantedItemInput.val().trim().length > 0;
            }

            return (
                selectedImageIsValid &&
                titleIsValid &&
                descriptionIsValid &&
                typeFieldsAreValid
            );
        }

        function updateFormValidity() {
            const formIsValid = isFormValid();

            $submitButton
                .prop("disabled", !formIsValid)
                .attr(
                    "title",
                    formIsValid
                        ? "거래 글을 등록합니다."
                        : "필수 정보를 모두 입력해 주세요."
                );
        }

        $typeInputs.on("change", updateTypeFields);

        $acceptAnything.on("change", function () {
            const acceptsAnything =
                $acceptAnything.is(":checked");

            $wantedItemInput
                .prop("disabled", acceptsAnything)
                .prop("required", !acceptsAnything);
            updateFormValidity();
        });

        $imageInput.on("change", function () {
            const file = this.files[0];

            if (!file) {
                showImageError("물품 사진을 선택해 주세요.");
                updateFormValidity();
                return;
            }

            if (!allowedImageTypes.includes(file.type)) {
                this.value = "";
                showImageError(
                    "JPG, PNG 또는 WEBP 이미지만 선택할 수 있습니다."
                );
                updateFormValidity();
                return;
            }

            if (file.size > maximumImageSize) {
                this.value = "";
                showImageError(
                    "이미지 크기는 5MB 이하여야 합니다."
                );
                updateFormValidity();
                return;
            }

            selectedImageIsValid = true;
            $imageInput.removeClass("is-invalid");
            $imageError.text("");
            updateImagePreview(file);
            updateFormValidity();
        });

        $descriptionInput.on("input", function () {
            $descriptionCount.text($(this).val().length);
            updateFormValidity();
        });

        $titleInput.on("input", updateFormValidity);
        $priceInput.on("input", updateFormValidity);
        $wantedItemInput.on("input", updateFormValidity);

        $form.on("submit", function (event) {
            if (!isFormValid()) {
                event.preventDefault();
                $form.addClass("was-validated");
                updateFormValidity();
            }
        });

        updateTypeFields();
        updateFormValidity();
    }

    function initializeItemStatusToggle() {
        const $toggleButton = $("#toggleItemStatus");
        const $detailPage = $(".item-detail-page");

        if ($toggleButton.length === 0 || $detailPage.length === 0) {
            return;
        }

        const itemId = $detailPage.data("itemId");
        const $statusBadge = $("#itemStatusBadge");
        const $imageWrap = $(".item-detail-image-wrap");

        function updateStatusUI(status) {
            const isDone = status === "done";

            $statusBadge
                .toggleClass("text-bg-dark", isDone)
                .toggleClass("text-bg-secondary", !isDone)
                .text(isDone ? "완료" : "판매 중");

            $toggleButton.text(
                isDone
                    ? "거래완료 해제"
                    : "거래완료 처리"
            );

            $toggleButton.toggleClass(
                "item-status-button-done",
                isDone
            );

            $imageWrap.toggleClass(
                "item-detail-image-done",
                isDone
            );
        }

        $toggleButton.on("click", async function () {
            $toggleButton.prop("disabled", true);

            try {
                const response = await fetch(
                    `/api/items/${itemId}/status`,
                    {
                        method: "POST"
                    }
                );
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(
                        data.error || "status_update_failed"
                    );
                }

                updateStatusUI(data.status);
            } catch (error) {
                alert(
                    "거래 상태를 변경하지 못했습니다. " +
                    "잠시 후 다시 시도해 주세요."
                );
                console.error(error);
            } finally {
                $toggleButton.prop("disabled", false);
            }
        });
    }
});
