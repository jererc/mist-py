var showDelay;

function initActions() {
    $('.content_element').mouseenter(function() {
        $(this).addClass('element_highlight');
        var element = $(this).find('.element_info');
        showDelay = setTimeout(function () {
            element.slideDown('fast');
        }, 600);
    });
    $('.content_element').mouseleave(function() {
        clearTimeout(showDelay);
        $(this).removeClass('element_highlight');
        $(this).find('.element_info').delay(2000).slideUp('slow');
    });

    $('.img_button[alt="edit"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $(div).find('.element_edit').slideToggle('fast');
        $(div).find('.save_action').fadeToggle('fast');
        return false;
    });

    $('.img_button[alt="add"]').bind('click', function() {
        var div = $(this).parents('.content_new')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/add',
            $(div).find('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img_button[alt="update"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/update',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img_button[alt="reset"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/reset',
            $(this).parents('form').serializeArray(),
            function(data) {
                if (data.result) {
                    location.reload();
                }
            });
        return false;
    });

    $('.img_button[alt="remove"]').bind('click', function() {
        var div = $(this).parents('.content_element')[0];
        $.getJSON($SCRIPT_ROOT + '/syncs/remove',
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
