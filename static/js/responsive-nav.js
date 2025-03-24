document.addEventListener('DOMContentLoaded', function() {
  // Sélectionner les éléments du DOM
  const menuToggle = document.querySelector('.menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  
  // Vérifier si les éléments existent
  if (menuToggle && navLinks) {
    // Ajouter un écouteur d'événement pour le clic sur le menu hamburger
    menuToggle.addEventListener('click', function() {
      // Basculer la classe active sur les liens de navigation
      navLinks.classList.toggle('active');
      
      // Basculer la classe active sur le menu hamburger pour l'animation
      menuToggle.classList.toggle('active');
    });
    
    // Fermer le menu lorsqu'un lien est cliqué
    const navItems = navLinks.querySelectorAll('a, button');
    navItems.forEach(item => {
      item.addEventListener('click', function() {
        navLinks.classList.remove('active');
        menuToggle.classList.remove('active');
      });
    });
    
    // Fermer le menu lorsqu'on clique en dehors
    document.addEventListener('click', function(event) {
      if (!navLinks.contains(event.target) && !menuToggle.contains(event.target)) {
        navLinks.classList.remove('active');
        menuToggle.classList.remove('active');
      }
    });
  }
  
  // Ajouter une classe au body pour indiquer la taille de l'écran
  function updateScreenSizeClass() {
    const body = document.body;
    if (window.innerWidth <= 480) {
      body.classList.add('is-mobile');
      body.classList.remove('is-tablet', 'is-desktop');
    } else if (window.innerWidth <= 768) {
      body.classList.add('is-tablet');
      body.classList.remove('is-mobile', 'is-desktop');
    } else {
      body.classList.add('is-desktop');
      body.classList.remove('is-mobile', 'is-tablet');
    }
  }
  
  // Appeler la fonction au chargement
  updateScreenSizeClass();
  
  // Mettre à jour la classe lors du redimensionnement de la fenêtre
  window.addEventListener('resize', updateScreenSizeClass);
});