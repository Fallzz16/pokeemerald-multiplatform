Kanto_Harbor_MapScripts::
	.byte 0

Kanto_Harbor_EventScript_ReturnFerry::
	lock
	faceplayer
	msgbox Kanto_Harbor_Text_ReturnToHoenn, MSGBOX_YESNO
	goto_if_eq VAR_RESULT, NO, Kanto_Harbor_EventScript_Stay
	closemessage
	warp MAP_SLATEPORT_CITY_HARBOR, 13, 12
	waitstate
	release
	end

Kanto_Harbor_EventScript_Stay::
	msgbox Kanto_Harbor_Text_Stay, MSGBOX_DEFAULT
	release
	end

Kanto_Harbor_Text_ReturnToHoenn:
	.string "Sail back to SLATEPORT in HOENN?$"

Kanto_Harbor_Text_Stay:
	.string "Enjoy your stay in KANTO!$"
