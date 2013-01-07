var hasFocus = true;

function handleFocus() {
    $(window).blur(function() {
        hasFocus = false;
    });
    $(window).focus(function() {
        hasFocus = true;
    });
};

function initBaseActions() {
    $('.content_element').mouseenter(function() {
        $(this).addClass('element_highlight');
        $(this).find('.element_actions').show();
    });
    $('.content_element').mouseleave(function() {
        $(this).removeClass('element_highlight');
        $(this).find('.element_actions').hide();
    });

    $('.img_button[alt="add"]').mouseenter(function() {
        var content = $(this).parents('.content_new')[0];
        $(content).addClass('element_highlight', 200);
        $(content).find('.element_new').slideDown('fast');
    });
    $('.content_new').mouseleave(function() {
        $(this).find('.element_new').slideUp('slow', function() {
            $('.content_new').removeClass('element_highlight', 200);
        });
    });
};

$(function() {
    handleFocus();
    initBaseActions();
});
