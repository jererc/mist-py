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

    $('.img_button[alt="add"]').mouseover(function() {
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
