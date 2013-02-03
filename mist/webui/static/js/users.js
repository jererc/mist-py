function initActions() {
    $('.img-button[alt="edit"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $(div).find('.element-edit').slideToggle('fast');
        $(div).find('.save-action').fadeToggle('fast');
        return false;
    });

    $('.img-button[alt="add"]').click(function() {
        var div = $(this).parents('.content-new')[0];
        var form = $(div).find('form');
        form.find('.default-text').each(function() {
            if ($(this).val() == this.title) {
                $(this).val("");
            }
        });

        $.getJSON($SCRIPT_ROOT + '/users/add',
            form.serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img-button[alt="update"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $.getJSON($SCRIPT_ROOT + '/users/update',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img-button[alt="remove"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $.getJSON($SCRIPT_ROOT + '/users/remove',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    $(div).fadeOut('fast');
                }
            });
        return false;
    });
};

$(function() {
    initActions();
});
