$('form').delay(1000).addClass('ouvert');


// En sortant d'un champ du Form (désélection)
$('input,textarea').blur(function () {
  if($(this).siblings('label').attr('for')=='msg'){ // Si c'est le textarea Message
    $(this).parent().css('margin-bottom','0'); // On retire la marge (qui baisse le bouton submit)
  }
  if ( $(this).val() != '' ) { // Si le champs est rempli
    $(this).siblings('label').addClass('labelOuvert'); // On laisse le label en petit
    if($(this).siblings('label').attr('for')=='msg'){ // Si c'est le champ message
      $(this).parent().addClass('messOuvert'); // Ajout de la classe pour agrandir le champ
      $(this).parent().css('margin-bottom','100px'); // On baisse le bouton
    }
  }
  else {
    $(this).siblings('label').removeClass('labelOuvert');
    if($(this).siblings('label').attr('for')=='msg'){ // Si c'est le textarea Message
      $(this).parent().removeClass('messOuvert'); // Retrait de la classe pour reduire le champ
    }
  }
});

$('textarea').focus(function () { // Au clic sur le textarea Message
  if($(this).val() == ''){ // Si le champ est vide
    $(this).parent().css('margin-bottom','100px'); // Rajout de la marge pour baisser le bouton submit
  }
});