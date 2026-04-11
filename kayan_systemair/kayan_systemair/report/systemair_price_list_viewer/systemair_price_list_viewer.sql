SELECT
    i.item_code          AS `Item Code`,
    i.item_name          AS `Item Name`,
    i.item_group         AS `Product Group`,
    ip_de.price_list_rate AS `Germany Price (EUR)`,
    ip_my.price_list_rate AS `Malaysia Price (EUR)`,
    i.sa_primary_factory  AS `Factory`,
    GREATEST(
        COALESCE(ip_de.modified, '1970-01-01'),
        COALESCE(ip_my.modified, '1970-01-01')
    )                     AS `Last Updated`
FROM `tabItem` i
LEFT JOIN `tabItem Price` ip_de
    ON ip_de.item_code = i.item_code
    AND ip_de.price_list = 'Systemair Germany 2026'
    AND ip_de.selling = 1
LEFT JOIN `tabItem Price` ip_my
    ON ip_my.item_code = i.item_code
    AND ip_my.price_list = 'Systemair Malaysia 2026'
    AND ip_my.selling = 1
WHERE
    i.item_group = 'SystemAir Axial Fans'
    AND i.disabled = 0
    AND (ip_de.price_list_rate IS NOT NULL OR ip_my.price_list_rate IS NOT NULL)
ORDER BY
    i.item_code ASC
