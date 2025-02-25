document.addEventListener('DOMContentLoaded', function() {
    // Récupérer les données JSON du template
    const dataElement = document.getElementById('host-data');
    const appData = JSON.parse(dataElement.textContent);
    
    // Extraire les variables
    const isHostActive = appData.isHostActive;
    const host = appData.host;
    const lastConnectionTime = appData.lastConnectionTime;
    
    console.log("Host status:", isHostActive ? "Active" : "Inactive");
    
    // Construire les URLs de base
    let baseCpuUrl = `http://localhost:3001/d-solo/dee0o5db5zgn4f/armin-graph?orgId=1&timezone=browser&panelId=1&var-host=${host}`;
    let baseDiskUrl = `http://localhost:3001/d-solo/dee0o5db5zgn4f/armin-disk?orgId=1&timezone=browser&panelId=2&var-host=${host}`;
    
    // Définir le comportement de rafraîchissement
    if (isHostActive) {
        console.log("Host is active, using live data");
        baseCpuUrl += "&refresh=5s";
        baseDiskUrl += "&refresh=5s";
    } else {
        console.log("Host is inactive, disabling refresh");
        baseCpuUrl += "&refresh=0";
        baseDiskUrl += "&refresh=0";
    }
    
    // Initialiser avec la plage de temps par défaut
    const timeRange = "60m";
    let initialCpuUrl, initialDiskUrl;
    
    if (isHostActive) {
        // Pour les hôtes actifs - plage relative standard
        initialCpuUrl = baseCpuUrl + "&from=now-" + timeRange + "&to=now";
        initialDiskUrl = baseDiskUrl + "&from=now-" + timeRange + "&to=now";
    } else if (lastConnectionTime) {
        // Pour les hôtes inactifs - plage centrée sur la dernière connexion
        const lastConnDate = new Date(lastConnectionTime);
        const lastConnTimestampMs = lastConnDate.getTime();
        
        // On utilise un point fixe pour "to" (dernière connexion + 5min)
        const endTimeMs = lastConnTimestampMs + (5 * 60 * 1000);
        // Le "from" sera dynamique selon la plage sélectionnée
        const startTimeMs = endTimeMs - (convertTimeRangeToMs(timeRange));
        
        console.log("Using fixed time range with end time:", new Date(endTimeMs).toISOString());
        
        initialCpuUrl = baseCpuUrl + "&from=" + startTimeMs + "&to=" + endTimeMs;
        initialDiskUrl = baseDiskUrl + "&from=" + startTimeMs + "&to=" + endTimeMs;
    } else {
        // Cas de secours si pas de lastConnectionTime
        initialCpuUrl = baseCpuUrl + "&from=now-" + timeRange + "&to=now";
        initialDiskUrl = baseDiskUrl + "&from=now-" + timeRange + "&to=now";
    }
    
    console.log("Initial CPU URL:", initialCpuUrl);
    console.log("Initial Disk URL:", initialDiskUrl);
    
    // Mettre à jour les iframes
    document.getElementById("cpu_iframe").src = initialCpuUrl;
    document.getElementById("disk_iframe").src = initialDiskUrl;
    
    // Fonction pour convertir les plages temporelles en millisecondes
    function convertTimeRangeToMs(range) {
        const value = parseInt(range.replace(/[^0-9]/g, ''));
        const unit = range.replace(/[0-9]/g, '');
        
        switch(unit) {
            case 'm': return value * 60 * 1000;
            case 'h': return value * 60 * 60 * 1000;
            case 'd': return value * 24 * 60 * 60 * 1000;
            default: return value * 60 * 1000; // Par défaut, minutes
        }
    }
    
    // Gérer le changement de plage de temps
    document.getElementById("time_range").addEventListener("change", function() {
        var range = this.value;
        var newCpuUrl, newDiskUrl;
        
        if (isHostActive) {
            // Pour les hôtes actifs - plage relative standard
            newCpuUrl = baseCpuUrl + "&from=now-" + range + "&to=now";
            newDiskUrl = baseDiskUrl + "&from=now-" + range + "&to=now";
        } else if (lastConnectionTime) {
            // Pour les hôtes inactifs - plage centrée autour de la dernière connexion
            const lastConnDate = new Date(lastConnectionTime);
            const lastConnTimestampMs = lastConnDate.getTime();
            
            // Point fixe pour "to" (dernière connexion + 5min)
            const endTimeMs = lastConnTimestampMs + (5 * 60 * 1000);
            // "from" dynamique basé sur la plage sélectionnée
            const startTimeMs = endTimeMs - (convertTimeRangeToMs(range));
            
            newCpuUrl = baseCpuUrl + "&from=" + startTimeMs + "&to=" + endTimeMs;
            newDiskUrl = baseDiskUrl + "&from=" + startTimeMs + "&to=" + endTimeMs;
        } else {
            // Cas de secours
            newCpuUrl = baseCpuUrl + "&from=now-" + range + "&to=now";
            newDiskUrl = baseDiskUrl + "&from=now-" + range + "&to=now";
        }
        
        console.log("New time range:", range);
        console.log("New CPU URL:", newCpuUrl);
        console.log("New Disk URL:", newDiskUrl);
        
        document.getElementById("cpu_iframe").src = newCpuUrl;
        document.getElementById("disk_iframe").src = newDiskUrl;
    });
});