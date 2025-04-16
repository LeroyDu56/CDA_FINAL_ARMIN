document.addEventListener('DOMContentLoaded', function() {
    // Sélectionner les éléments du DOM
    const addHostBtn = document.getElementById('add-host-btn');
    const addHostModal = document.getElementById('add-host-modal');
    const closeHostModal = document.querySelector('.close-host-modal');
    const cancelAddHost = document.getElementById('cancel-add-host');
    
    // Ouvrir le popup
    if (addHostBtn) {
        addHostBtn.addEventListener('click', function() {
            addHostModal.style.display = 'flex';
        });
    }
    
    // Fermer le popup avec le bouton X
    if (closeHostModal) {
        closeHostModal.addEventListener('click', function() {
            addHostModal.style.display = 'none';
        });
    }
    
    // Fermer le popup avec le bouton Annuler
    if (cancelAddHost) {
        cancelAddHost.addEventListener('click', function(e) {
            e.preventDefault();
            addHostModal.style.display = 'none';
        });
    }
    
    // Fermer le popup en cliquant en dehors
    window.addEventListener('click', function(event) {
        if (event.target === addHostModal) {
            addHostModal.style.display = 'none';
        }
    });
    
    // Validation du formulaire côté client
    const addHostForm = document.getElementById('add-host-form');
    if (addHostForm) {
        addHostForm.addEventListener('submit', function(e) {
            const hostName = document.getElementById('host_name').value.trim();
            const ipAddress = document.getElementById('ip_address').value.trim();
            
            // Validation simple
            if (!hostName) {
                e.preventDefault();
                alert('Veuillez entrer un nom d\'hôte');
                return false;
            }
            
            if (!ipAddress) {
                e.preventDefault();
                alert('Veuillez entrer une adresse IP');
                return false;
            }
            
            // Validation basique du format d'IP (IPv4)
            const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
            if (!ipPattern.test(ipAddress)) {
                e.preventDefault();
                alert('Veuillez entrer une adresse IP valide (format: xxx.xxx.xxx.xxx)');
                return false;
            }
            
            return true;
        });
    }
});