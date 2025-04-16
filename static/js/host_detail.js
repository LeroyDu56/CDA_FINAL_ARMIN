document.addEventListener('DOMContentLoaded', function() {
    // Récupérer les données JSON du template
    const appData = JSON.parse(document.getElementById('host-data').textContent);
    
    const { 
        isHostActive, 
        host, 
        lastConnectionTime, 
        grafanaBaseUrl
    } = appData;
    
    // Définir les IDs de panneau selon l'ordre dans Grafana
    // 1=CPU, 2=Mémoire, 3=Disque, 4=Nombre processus, 5=SWAP, 6=Trafic réseau, 7=Charge système
    const panels = {
        cpu: {
            id: 1,  // Semble correct
            element: "cpu_iframe",
            dashboard: "armin_graph"
        },
        memory: {
            id: 3,  // À déterminer - actuellement "Panel not found"
            element: "memory_iframe",
            dashboard: "armin_graph"
        },
        disk: {
            id: 4,  // Actuellement affiche Mémoire, donc ID=2
            element: "disk_iframe",
            dashboard: "armin_graph"
        },
        processes: {
            id: 8,  // Semble correct
            element: "processes_iframe",
            dashboard: "armin_graph"
        },
        swap: {
            id: 7,  // Actuellement affiche Charge système, donc ID=7
            element: "swap_iframe",
            dashboard: "armin_graph"
        },
        network: {
            id: 6,  // Semble correct
            element: "network_iframe",
            dashboard: "armin_graph"
        },
        system: {
            id: 5,  // Actuellement affiche SWAP, donc ID=5
            element: "load_iframe",
            dashboard: "armin_graph"
        }
    };
    
    // Construire les URLs de base avec le refresh approprié
    const refreshParam = isHostActive ? "&refresh=5s" : "&refresh=0";
    
    // Fonction pour convertir les plages temporelles en millisecondes
    function convertTimeRangeToMs(range) {
        const value = parseInt(range.replace(/[^0-9]/g, ''));
        const unit = range.replace(/[0-9]/g, '');
        
        const multipliers = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000
        };
        
        return value * (multipliers[unit] || 60 * 1000);
    }
    
    // Fonction pour générer l'URL d'un panneau
    function generatePanelUrl(panel, timeRange) {
        const baseUrl = `${grafanaBaseUrl}/${panel.dashboard}?orgId=1&timezone=browser&panelId=${panel.id}&var-host=${host}${refreshParam}`;
        
        if (isHostActive) {
            return `${baseUrl}&from=now-${timeRange}&to=now`;
        } 
        
        if (lastConnectionTime) {
            const lastConnDate = new Date(lastConnectionTime);
            const endTimeMs = lastConnDate.getTime() + (5 * 60 * 1000);
            const startTimeMs = endTimeMs - convertTimeRangeToMs(timeRange);
            
            return `${baseUrl}&from=${startTimeMs}&to=${endTimeMs}`;
        }
        
        // Cas par défaut
        return `${baseUrl}&from=now-${timeRange}&to=now`;
    }
    
    // Mettre à jour tous les iframes
    function updateIframes(timeRange) {
        // Parcourir tous les panneaux et mettre à jour leurs iframes
        Object.values(panels).forEach(panel => {
            const iframe = document.getElementById(panel.element);
            if (iframe) {
                iframe.src = generatePanelUrl(panel, timeRange);
            }
        });
    }
    
    // Initialiser avec la plage de temps par défaut
    updateIframes("60m");
    
    // Gérer le changement de plage de temps
    const timeRangeSelector = document.getElementById("time_range");
    if (timeRangeSelector) {
        timeRangeSelector.addEventListener("change", function() {
            updateIframes(this.value);
        });
    }

    // Fonction pour mettre à jour l'affichage de la dernière connexion
    function updateLastConnectionTime() {
        const lastConnectionElement = document.getElementById('last-connection');
        
        if (!lastConnectionElement) return;
        
        if (lastConnectionTime && isHostActive !== true) {
            const lastConnDate = new Date(lastConnectionTime);
            const now = new Date();
            const timeDiff = Math.floor((now - lastConnDate) / 1000); // différence en secondes

            let displayText = "";
            if (timeDiff < 60) {
                displayText = "Il y a quelques secondes";
            } else if (timeDiff < 3600) {
                const minutes = Math.floor(timeDiff / 60);
                displayText = `Il y a ${minutes} minute${minutes > 1 ? 's' : ''}`;
            } else if (timeDiff < 86400) {
                const hours = Math.floor(timeDiff / 3600);
                displayText = `Il y a ${hours} heure${hours > 1 ? 's' : ''}`;
            } else if (timeDiff < 2592000) { // moins de 30 jours
                const days = Math.floor(timeDiff / 86400);
                displayText = `Il y a ${days} jour${days > 1 ? 's' : ''}`;
            } else {
                // Format: DD/MM/YYYY
                const day = lastConnDate.getDate().toString().padStart(2, '0');
                const month = (lastConnDate.getMonth() + 1).toString().padStart(2, '0');
                const year = lastConnDate.getFullYear();
                displayText = `Dernière connexion le ${day}/${month}/${year}`;
            }

            lastConnectionElement.textContent = displayText;
        }
    }

    // Mettre à jour l'affichage toutes les minutes
    updateLastConnectionTime();
    setInterval(updateLastConnectionTime, 60000);

    // Gestion du formulaire d'édition client
    const clientDisplay = document.getElementById('client-display');
    const editClientBtn = document.getElementById('edit-client-btn');
    const clientEditForm = document.getElementById('client-edit-form');
    const clientInput = document.getElementById('client-input');
    const saveClientBtn = document.getElementById('save-client-btn');
    const cancelClientEdit = document.getElementById('cancel-client-edit');
    
    // Fonction pour envoyer les mises à jour via AJAX
    function updateClientName(value) {
        const formData = new FormData();
        formData.append('update_field', 'client');
        formData.append('client', value);
        formData.append('host', host);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        
        fetch('/update_host_info/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur réseau');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                clientDisplay.textContent = value;
                clientEditForm.style.display = 'none';
                clientDisplay.style.display = 'inline';
                editClientBtn.style.display = 'inline-block';
            } else {
                alert('Erreur lors de la mise à jour: ' + (data.error || 'Erreur inconnue'));
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour: ' + error.message);
        });
    }
    
    if (editClientBtn) {
        editClientBtn.addEventListener('click', function() {
            clientDisplay.style.display = 'none';
            editClientBtn.style.display = 'none';
            clientEditForm.style.display = 'block';
            clientInput.focus();
            clientInput.select();
        });
    }
    
    if (saveClientBtn) {
        saveClientBtn.addEventListener('click', function() {
            const newClient = clientInput.value.trim();
            if (newClient) {
                updateClientName(newClient);
            } else {
                alert('Le nom du client ne peut pas être vide');
            }
        });
        
        // Permettre l'envoi avec la touche Entrée
        if (clientInput) {
            clientInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    saveClientBtn.click();
                }
            });
        }
    }
    
    if (cancelClientEdit) {
        cancelClientEdit.addEventListener('click', function() {
            clientInput.value = clientDisplay.textContent;
            clientEditForm.style.display = 'none';
            clientDisplay.style.display = 'inline';
            editClientBtn.style.display = 'inline-block';
        });
    }

    // Gestion des popups d'action
    const quickLinksBtn = document.getElementById('quick-links-btn');
    const quickLinksPopup = document.getElementById('quick-links-popup');
    const closePopupBtns = document.querySelectorAll('.close-popup');
    
    // Ouvrir le popup des liens rapides
    if (quickLinksBtn && quickLinksPopup) {
        quickLinksBtn.addEventListener('click', function() {
            quickLinksPopup.style.display = 'flex';
        });
    }
    
    // Fermer les popups
    closePopupBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const popup = this.closest('.action-popup');
            if (popup) {
                popup.style.display = 'none';
            }
        });
    });
    
    // Fermer les popups en cliquant en dehors
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('action-popup')) {
            event.target.style.display = 'none';
        }
    });

        // Gestion du popup Contact
    const contactBtn = document.getElementById('contact-btn');
    const contactPopup = document.getElementById('contact-popup');

    // Éléments du mode affichage
    const contactDisplay = document.getElementById('contact-display');
    const contactNameDisplay = document.getElementById('contact-name-display');
    const contactEmailDisplay = document.getElementById('contact-email-display');
    const contactPhoneDisplay = document.getElementById('contact-phone-display');
    const editContactBtn = document.getElementById('edit-contact-btn');

    // Éléments du mode édition
    const contactEditForm = document.getElementById('contact-edit-form');
    const contactNameInput = document.getElementById('contact-name-input');
    const contactEmailInput = document.getElementById('contact-email-input');
    const contactPhoneInput = document.getElementById('contact-phone-input');
    const saveContactBtn = document.getElementById('save-contact-btn');
    const cancelContactEdit = document.getElementById('cancel-contact-edit');

    // Ouvrir le popup Contact
    if (contactBtn && contactPopup) {
        contactBtn.addEventListener('click', function(event) {
            console.log("Bouton Contact cliqué!");
            contactPopup.style.display = 'flex';
            event.stopPropagation();
        });
    }

    // Passer en mode édition de contact
    if (editContactBtn && contactEditForm && contactDisplay) {
        editContactBtn.addEventListener('click', function() {
            contactDisplay.style.display = 'none';
            contactEditForm.style.display = 'block';
            contactNameInput.focus();
        });
    }

    // Sauvegarder les modifications
    if (saveContactBtn) {
        saveContactBtn.addEventListener('click', function() {
            const name = contactNameInput.value.trim();
            const email = contactEmailInput.value.trim();
            const phone = contactPhoneInput.value.trim();
            
            // Validation simple pour l'email
            if (email && !isValidEmail(email)) {
                alert("Veuillez entrer une adresse email valide.");
                contactEmailInput.focus();
                return;
            }
            
            // Mise à jour de l'affichage
            contactNameDisplay.textContent = name || "Non renseigné";
            contactEmailDisplay.textContent = email || "Non renseigné";
            contactPhoneDisplay.textContent = phone || "Non renseigné";
            
            // Création d'une date formatée
            const now = new Date();
            const day = now.getDate().toString().padStart(2, '0');
            const month = (now.getMonth() + 1).toString().padStart(2, '0'); 
            const year = now.getFullYear();
            const hours = now.getHours().toString().padStart(2, '0');
            const minutes = now.getMinutes().toString().padStart(2, '0');
            
            const formattedDate = `${day}/${month}/${year} ${hours}:${minutes}`;
            
            // Sauvegarder les données via AJAX
            updateContactInfo(name, email, phone);
            
            // Revenir au mode affichage
            contactEditForm.style.display = 'none';
            contactDisplay.style.display = 'block';
        });
    }

    // Annuler l'édition
    if (cancelContactEdit) {
        cancelContactEdit.addEventListener('click', function() {
            // Revenir au mode affichage sans sauvegarder
            contactEditForm.style.display = 'none';
            contactDisplay.style.display = 'block';
        });
    }

    // Fonction pour mettre à jour les informations de contact via AJAX
    function updateContactInfo(name, email, phone) {
        const formData = new FormData();
        formData.append('update_field', 'contact');
        formData.append('contact_name', name);
        formData.append('contact_email', email);
        formData.append('contact_phone', phone);
        formData.append('host', host);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        
        fetch('/update_host_info/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur réseau');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log("Informations de contact mises à jour avec succès");
            } else {
                alert('Erreur lors de la mise à jour: ' + (data.error || 'Erreur inconnue'));
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour: ' + error.message);
        });
    }

    // Fonction de validation d'email
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // Fonction pour mettre à jour les informations de contact via AJAX
    function updateContactInfo(name, email, phone) {
        const formData = new FormData();
        formData.append('update_field', 'contact');
        formData.append('contact_name', name);
        formData.append('contact_email', email);
        formData.append('contact_phone', phone);
        formData.append('host', host);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        
        fetch('/update_host_info/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Erreur réseau');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log("Informations de contact mises à jour avec succès");
                
                // Mettre à jour la date de dernière modification si elle est fournie
                if (data.last_updated) {
                    document.getElementById('last-update-display').textContent = data.last_updated;
                }
            } else {
                alert('Erreur lors de la mise à jour: ' + (data.error || 'Erreur inconnue'));
            }
        })
        .catch(error => {
            console.error('Erreur:', error);
            alert('Erreur lors de la mise à jour: ' + error.message);
        });
    }

});