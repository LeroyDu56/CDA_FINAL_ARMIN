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
    document.getElementById("time_range").addEventListener("change", function() {
        updateIframes(this.value);
    });
});