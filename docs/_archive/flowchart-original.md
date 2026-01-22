flowchart TB
  internet((Internet)) --> wan[WAN]
  wan --> opn[OPNsense Firewall/Router<br/>Protectli Vault FW4C]

  opn --> sw[Managed Switch<br/>TP-Link TL-SG108E]
  sw --> ap[WiFi AP (Bridge Mode)<br/>AmpliFi Alien]

  subgraph vlans["VLANs / Subnets"]
    v10["VLAN10 MGMT<br/>10.10.10.0/24"]
    v20["VLAN20 SERVERS<br/>10.10.20.0/24"]
    v30["VLAN30 CLIENTS<br/>10.10.30.0/24"]
    v40["VLAN40 LAB<br/>10.10.40.0/24"]
    v50["VLAN50 IOT<br/>10.10.50.0/24"]
  end

  opn --- v10
  opn --- v20
  opn --- v30
  opn --- v40
  opn --- v50

  sw --> pve[Proxmox Host<br/>(runs VMs/LXCs)]
  sw --> adminpc[Admin Client(s)<br/>(PC/iPad via LAN/WiFi)]
  ap --> wifi_clients[WiFi Clients]
  ap --> wifi_iot[IoT WiFi Devices]

  subgraph services["Core Services"]
    dns[Pi-hole + Unbound<br/>Authoritative local + recursive DNS]
    obs[Telemetry/Observability<br/>Grafana + Loki + Promtail + Netdata]
    unifi[UniFi Network Controller<br/>(planned/active)]
    media[Rivendell Media Host<br/>Docker: Jellyfin/Audiobookshelf/*arr/qBittorrent+Gluetun]
  end

  pve --> dns
  pve --> obs
  pve --> unifi
  pve --> media

  classDef plane fill:#111,stroke:#666,stroke-width:1px,color:#fff;
  classDef service fill:#0b2,stroke:#070,stroke-width:1px,color:#fff;
  class opn,sw,ap,pve plane;
  class dns,obs,unifi,media service;
