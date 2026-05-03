(function () {
    'use strict';

    function renderOptions(selectField, items, selectedValue) {
        var options = ['<option value="">---------</option>'];

        items.forEach(function (item) {
            var selected = String(item.id) === String(selectedValue) ? ' selected' : '';
            options.push('<option value="' + item.id + '"' + selected + '>' + item.name + '</option>');
        });

        selectField.innerHTML = options.join('');

        if (selectedValue) {
            selectField.value = String(selectedValue);
        }
    }

    function renderOptionsMultiple(selectField, items, selectedValues) {
        var selectedLookup = {};
        (selectedValues || []).forEach(function (value) {
            selectedLookup[String(value)] = true;
        });

        var options = [];
        items.forEach(function (item) {
            var selected = selectedLookup[String(item.id)] ? ' selected' : '';
            options.push('<option value="' + item.id + '"' + selected + '>' + item.name + '</option>');
        });

        selectField.innerHTML = options.join('');
    }

    function getBrandOptionsUrl(brandField) {
        if (brandField.dataset.brandOptionsUrl) {
            return brandField.dataset.brandOptionsUrl;
        }
        return '/admin/catalog/product/brand-options/';
    }

    function setRelatedControlState(control, isEnabled) {
        if (!control) {
            return;
        }
        if (isEnabled) {
            control.style.pointerEvents = '';
            control.style.opacity = '';
            control.removeAttribute('aria-disabled');
            return;
        }
        control.style.pointerEvents = 'none';
        control.style.opacity = '0.5';
        control.setAttribute('aria-disabled', 'true');
    }

    function setBrandFieldState(categoryField, brandField) {
        var hasCategory = Boolean(categoryField.value);
        brandField.disabled = !hasCategory;
        setRelatedControlState(document.getElementById('add_' + brandField.id), hasCategory);
        setRelatedControlState(document.getElementById('change_' + brandField.id), hasCategory && Boolean(brandField.value));
        setRelatedControlState(document.getElementById('delete_' + brandField.id), hasCategory && Boolean(brandField.value));
        setRelatedControlState(document.getElementById('view_' + brandField.id), hasCategory && Boolean(brandField.value));
    }

    function updateBrandAddLink(categoryField, brandField) {
        var addLink = document.getElementById('add_' + brandField.id);
        if (!addLink) {
            return;
        }

        var baseUrl = addLink.dataset.baseHref || addLink.getAttribute('href');
        if (!baseUrl) {
            return;
        }

        addLink.dataset.baseHref = baseUrl.split('?')[0];

        var categoryId = categoryField.value;
        if (!categoryId) {
            addLink.setAttribute('href', addLink.dataset.baseHref);
            return;
        }

        addLink.setAttribute('href', addLink.dataset.baseHref + '?category=' + encodeURIComponent(categoryId));
    }

    function updateBrandOptions(categoryField, brandField) {
        var categoryId = categoryField.value;
        var selectedBrandId = brandField.value;
        var url = getBrandOptionsUrl(brandField);

        if (!categoryId) {
            renderOptions(brandField, [], '');
            return Promise.resolve();
        }

        return fetch(url + '?category_id=' + encodeURIComponent(categoryId), {
            credentials: 'same-origin'
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (payload) {
                renderOptions(brandField, payload.results || [], selectedBrandId);
            })
            .catch(function () {
                renderOptions(brandField, [], '');
            });
    }

    function getBreakdownGroupOptionsUrl(breakdownGroupField) {
        return breakdownGroupField.dataset.breakdownGroupOptionsUrl || '';
    }

    function updateBreakdownGroupOptions(categoryField, brandField, breakdownGroupField) {
        var categoryId = categoryField ? categoryField.value : '';
        var selectedGroupId = breakdownGroupField.value;
        var url = getBreakdownGroupOptionsUrl(breakdownGroupField);

        if (!url || !categoryId) {
            renderOptions(breakdownGroupField, [], '');
            return;
        }

        fetch(
            url + '?category_id=' + encodeURIComponent(categoryId),
            {
                credentials: 'same-origin'
            }
        )
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (payload) {
                renderOptions(breakdownGroupField, payload.results || [], selectedGroupId);
            })
            .catch(function () {
                renderOptions(breakdownGroupField, [], '');
            });
    }

    function updateAdditionalBreakdownGroupOptions(categoryField, additionalBreakdownGroupsField) {
        var categoryId = categoryField ? categoryField.value : '';
        var selectedGroupIds = Array.from(additionalBreakdownGroupsField.selectedOptions || []).map(function (option) {
            return option.value;
        });
        var url = getBreakdownGroupOptionsUrl(additionalBreakdownGroupsField);

        if (!url || !categoryId) {
            renderOptionsMultiple(additionalBreakdownGroupsField, [], []);
            return;
        }

        fetch(
            url + '?category_id=' + encodeURIComponent(categoryId),
            {
                credentials: 'same-origin'
            }
        )
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.json();
            })
            .then(function (payload) {
                renderOptionsMultiple(additionalBreakdownGroupsField, payload.results || [], selectedGroupIds);
            })
            .catch(function () {
                renderOptionsMultiple(additionalBreakdownGroupsField, [], []);
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var categoryField = document.getElementById('id_category') || document.querySelector('select[name="category"]');
        var brandField = document.getElementById('id_brand') || document.querySelector('select[name="brand"]');
        var breakdownGroupField = document.getElementById('id_breakdown_group') || document.querySelector('select[name="breakdown_group"]');
        var additionalBreakdownGroupsField = document.getElementById('id_breakdown_groups') || document.querySelector('select[name="breakdown_groups"]');

        if (!categoryField) {
            return;
        }

        if (brandField) {
            setBrandFieldState(categoryField, brandField);
            updateBrandAddLink(categoryField, brandField);

            categoryField.addEventListener('change', function () {
                setBrandFieldState(categoryField, brandField);
                updateBrandAddLink(categoryField, brandField);
                updateBrandOptions(categoryField, brandField).then(function () {
                    setBrandFieldState(categoryField, brandField);
                    if (breakdownGroupField) {
                        updateBreakdownGroupOptions(categoryField, brandField, breakdownGroupField);
                    }
                    if (additionalBreakdownGroupsField) {
                        updateAdditionalBreakdownGroupOptions(categoryField, additionalBreakdownGroupsField);
                    }
                });
            });

            brandField.addEventListener('change', function () {
                setBrandFieldState(categoryField, brandField);
                if (breakdownGroupField) {
                    updateBreakdownGroupOptions(categoryField, brandField, breakdownGroupField);
                }
                if (additionalBreakdownGroupsField) {
                    updateAdditionalBreakdownGroupOptions(categoryField, additionalBreakdownGroupsField);
                }
            });

            if (categoryField.value) {
                updateBrandOptions(categoryField, brandField).then(function () {
                    setBrandFieldState(categoryField, brandField);
                    if (breakdownGroupField) {
                        updateBreakdownGroupOptions(categoryField, brandField, breakdownGroupField);
                    }
                    if (additionalBreakdownGroupsField) {
                        updateAdditionalBreakdownGroupOptions(categoryField, additionalBreakdownGroupsField);
                    }
                });
            }
        }

        if (breakdownGroupField && !brandField) {
            updateBreakdownGroupOptions(categoryField, brandField, breakdownGroupField);
        }
        if (additionalBreakdownGroupsField && !brandField) {
            updateAdditionalBreakdownGroupOptions(categoryField, additionalBreakdownGroupsField);
        }
    });
})();
