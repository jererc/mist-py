function initActions() {
    $('.content-element').mouseenter(function() {
        $(this).addClass('element-highlight');
        toggleElement($(this).attr('data-id'),
                $(this).find('.element-details'), 'down', 600);
    });
    $('.content-element').mouseleave(function() {
        $(this).removeClass('element-highlight');
        toggleElement($(this).attr('data-id'),
                $(this).find('.element-details'), 'up', 2000);
    });

    $('.img-button[alt="more"]').click(function() {
        var div = $(this).parents('.content-element')[0];
        $(div).find('.element-info').slideToggle('fast');
        return false;
    });
};

function updateStatus() {
    $('.content-element').each(function(result) {
        var status = $(this).find('.host-status');

        $.getJSON($SCRIPT_ROOT + '/hosts/status',
            {id: $(this).find('input[name="id"]').val()},
            function(data) {
                if (data.result) {
                    status.removeClass('host-down').addClass('host-up');
                    status.html('up');
                } else {
                    status.removeClass('host-up').addClass('host-down');
                    status.html('down');
                }
            });
    });
};

$(function() {
    initActions();
    updateStatus();
    var statusInterval = window.setInterval(updateStatus, 5000);
});
