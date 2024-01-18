

case "$1" in
soumya) DIS_NUM='1' ;;
spl2) DIS_NUM='1' ;;
bijit) DIS_NUM='1' ;;
*) DIS_NUM='0' ;;
esac

ssh $1 "cd ~/Downloads; DISPLAY=:$DIS_NUM scrot -z -p -o -u .screenshot.png"
rsync -q $1:~/Downloads/.screenshot.png screen_shot.png --remove-source-files


