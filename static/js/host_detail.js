document.addEventListener('DOMContentLoaded', function() {
    // Récupérer les données JSON du template
    const appData = JSON.parse(document.getElementById('host-data').textContent);
    
    const { isHostActive, host, lastConnectionTime, grafanaBaseUrl, cpuPanelId, diskPanelId } = appData;
    
    // Construire les URLs de base
    const refreshParam = isHostActive ? "&refresh=5s" : "&refresh=0";
    const baseCpuUrl = `${grafanaBaseUrl}/armin-graph?orgId=1&timezone=browser&panelId=${cpuPanelId}&var-host=${host}${refreshParam}`;
    const baseDiskUrl = `${grafanaBaseUrl}/armin-disk?orgId=1&timezone=browser&panelId=${diskPanelId}&var-host=${host}${refreshParam}`;
    
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
    
    // Fonction pour générer les URLs selon les paramètres
    function generateUrls(timeRange) {
        if (isHostActive) {
            return {
                cpuUrl: `${baseCpuUrl}&from=now-${timeRange}&to=now`,
                diskUrl: `${baseDiskUrl}&from=now-${timeRange}&to=now`
            };
        } 
        
        if (lastConnectionTime) {
            const lastConnDate = new Date(lastConnectionTime);
            const endTimeMs = lastConnDate.getTime() + (5 * 60 * 1000);
            const startTimeMs = endTimeMs - convertTimeRangeToMs(timeRange);
            
            return {
                cpuUrl: `${baseCpuUrl}&from=${startTimeMs}&to=${endTimeMs}`,
                diskUrl: `${baseDiskUrl}&from=${startTimeMs}&to=${endTimeMs}`
            };
        }
        
        // Cas par défaut si aucune condition n'est remplie
        return {
            cpuUrl: `${baseCpuUrl}&from=now-${timeRange}&to=now`,
            diskUrl: `${baseDiskUrl}&from=now-${timeRange}&to=now`
        };
    }
    
    // Mettre à jour les iframes
    function updateIframes(timeRange) {
        const urls = generateUrls(timeRange);
        document.getElementById("cpu_iframe").src = urls.cpuUrl;
        document.getElementById("disk_iframe").src = urls.diskUrl;
    }
    
    // Initialiser avec la plage de temps par défaut
    updateIframes("60m");
    
    // Gérer le changement de plage de temps
    document.getElementById("time_range").addEventListener("change", function() {
        updateIframes(this.value);
    });
});