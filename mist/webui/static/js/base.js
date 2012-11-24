var has_focus = true;

function handleFocus() {
    $(window).blur(function(){
        has_focus = false;
        });
    $(window).focus(function(){
        has_focus = true;
        });
    };

function initBaseActions() {
    $('.content_element').mouseover(function() {
        $(this).addClass('element_highlight');
        $(this).find('.element_actions').show();
        });
    $('.content_element').mouseleave(function() {
        $(this).removeClass('element_highlight');
        $(this).find('.element_actions').hide();
        });

    $('.content_new').mouseover(function() {
        $(this).addClass('element_highlight');
        $(this).find('.element_new').slideDown('fast');
        });
    $('.content_new').mouseleave(function() {
        $(this).find('.element_new').slideUp('fast', function() {
            $('.content_new').removeClass('element_highlight');
            });
        });
    };

$(function() {
    handleFocus();
    initBaseActions();
    });
