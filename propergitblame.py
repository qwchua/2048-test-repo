import click
from gc import collect
import re
import subprocess
from matplotlib import pyplot as plt
import time
import concurrent.futures

def getStarts(line):
    pattern = re.compile(r'@@\s-\d*,?\d*\s\+\d*,?\d* @@')
    match = pattern.findall(line)
    match = match[0]
    matches = match.split()

    start1 = matches[1][1:].split(',')[0]
    start2 = matches[2][1:].split(',')[0]

    return int(start1), int(start2)

# @click.command()
# @click.option('--name', '-n', help="Name of the person to say hello", required=True)
# def propergitblame(name):
#     print("Hello world!" + name)

@click.command()
@click.option("-f", "--filename", type=str)
@click.option("-n", "--numberofcommits", type=int, default = 200)
@click.option("-o", "--output", type=str, default = "annotate")
def propergitblame(filename, output, numberofcommits):
    if filename == "all":
        print("Checking contributions for all files tracked by git!")
        getAllTrackedFiles = "git ls-tree -r main --name-only"
        command = subprocess.run(getAllTrackedFiles, shell=True, capture_output=True, text=True)
        unparsed_show = command.stdout
        unparsed_show = unparsed_show.split('\n')
        listOfFilesTrackedByGit = unparsed_show[:-1]
        lisfOfFilesEndingWithJs = []
        for l in listOfFilesTrackedByGit:
            if l[-3:len(l)] == ".js":
                lisfOfFilesEndingWithJs.append(l)
        t1 = time.perf_counter()

        with concurrent.futures.ProcessPoolExecutor() as executor:
            executor.map(getScoreboardwithoutnumberofcommits, lisfOfFilesEndingWithJs)
        t2 = time.perf_counter()

        print(f'Finished in {t2-t1}')

    else:
        t1 = time.perf_counter()
        scoreboard = getScoreboard(filename, numberofcommits)
        
        if(output == "piechart"):
            print("Displaying piechart!")
            dict = {}
            for i in range(1, len(scoreboard)):
                author = scoreboard[i]
                if author in dict.keys():
                    #key exists
                    dict[author] += 1
                else:
                    dict[author] = 1

            slices = []
            labels = []

            for k in dict:
                slices.append(dict[k])
                labels.append(k)

            plt.pie(slices,labels=labels,shadow=True, wedgeprops={'edgecolor':'black'},startangle=90, autopct='%1.1f%%')

            plt.title("Contribution pie chart for {}".format(filename))
            plt.tight_layout()
            plt.show()



            plt.style.use("fivethirtyeight")


        elif(output == "annotate"):
            print("Display annotate!")
            gitshowcommand = "git show HEAD:{}".format(filename)

            show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
            unparsed_show = show.stdout
            unparsed_show = unparsed_show.split('\n')

            output = []
            for i in range(1, len(scoreboard)):
                author = scoreboard[i][:20].ljust(22)
                output.append("{}{}) {}".format(author, i, unparsed_show[i-1]))
            
            for o in output:
                print(o)
        
        t2 = time.perf_counter()
        print(f'Finished in {t2-t1}s')





def getScoreboard(filename, numberofcommits=200):
    gitlogcommand = 'git log -n {} --pretty="format:%H:%an:%ae:%cD" -- {} '.format(numberofcommits,filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []
    print("File was found in : {} commits".format(len(collection)))
    print("Analyzing...")


    for c in collection:
        #remove the /n in end of the string
        c = c[:-2]

        list = c.split(":")

        commit = {
            "hash": list[0],
            "author": list[1],
            "email": list[2],
            "date": list[3],
        }
        commitgraph.append(commit)

    commitgraph.reverse()

    gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

    show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
    unparsed_show = show.stdout
    count = len(unparsed_show.split('\n'))

    #remember to change index 0 to null; line0 = index 0
    scoreboard = [commitgraph[0]["author"]] * (count + 1)

    #print scoreboard
    #for i in range(1,len(scoreboard)):
        #print("{} : {}".format(i, scoreboard[i]))

    for i in range(len(commitgraph)-1):
    #for i in range(2):
        commithash0 = commitgraph[i]['hash']
        commithash1 = commitgraph[i+1]['hash']
        #print("{} Doing hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        gitdiffcommand = "git diff -U0 --numstat {} {} -- {}".format(commithash0,commithash1,filename)

        diff = subprocess.run(gitdiffcommand, shell=True, capture_output=True, text=True)
        unparsed_diff = diff.stdout
        #print(unparsed_diff)
        unparsed_diff = unparsed_diff.split("\n")
        #print(unparsed_diff[-1])
        start1 = 0
        start2 = 0

        queue1 = []
        queue2 = []

        negcurr = 0
        balance = 0

        for x in range(6, len(unparsed_diff)):
        #for x in range(6, len(unparsed_diff)):
            if len(unparsed_diff[x]) == 0 or unparsed_diff[x][0] == "@":
                while(queue1 or queue2):
                    if(queue1 and queue2 and queue1[0]["line"] == queue2[0]["line"]):
                        #do listen algo here
                        #current I set as who edited last
                        scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
                        #print("Edited line {}".format(queue1[0]["line"]))
                        queue1.pop(0)
                        queue2.pop(0)
                    elif(queue1):
                        lineToStartPoppingAt = queue1[0]["line"]
                        while(queue1):
                                scoreboard.pop(lineToStartPoppingAt)
                                #print("Deleted line {}".format(lineToStartPoppingAt))
                                balance-=1
                                queue1.pop(0)
                                #print("Scoreboard len: {}".format(len(scoreboard)))
                    elif(queue2):
                        scoreboard.insert(queue2[0]["line"], commitgraph[i+1]['author'])
                        #print("Added on line {}".format(queue2[0]["line"]))
                        balance+=1
                        queue2.pop(0)
                    else:
                        print("Something went wrong while testing even")
                #print("Scoreboard len: {}".format(len(scoreboard)))

                if(len(unparsed_diff[x]) != 0):
                    start1, start2 = getStarts(unparsed_diff[x])
            elif unparsed_diff[x][0] == "-":
                queue1.append({"line":start1+balance, "content": unparsed_diff[1:]})
                start1+=1
            elif unparsed_diff[x][0] == "+":
                queue2.append({"line":start2, "content": unparsed_diff[1:]})
                start2+=1
            
        #print("Round{} Scoreboard for hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        #for i in range(1,len(scoreboard)):
            #print("{} : {}".format(i, scoreboard[i]))

    return scoreboard

    #for i in range(1,len(scoreboard)):
        #click.echo("{} : {}".format(i, scoreboard[i]))

def getScoreboardwithoutnumberofcommits(filename):
    print("Doing " + filename + " now!")
    gitlogcommand = 'git log --pretty="format:%H:%an:%ae:%cD" -- {} '.format(filename)
    unparsedlog = subprocess.run(gitlogcommand, shell=True, capture_output=True, text=True)
    unparsedlogstring = unparsedlog.stdout
    collection = unparsedlogstring.split('\n')
    commitgraph = []


    for c in collection:
        #remove the /n in end of the string
        c = c[:-2]

        list = c.split(":")

        commit = {
            "hash": list[0],
            "author": list[1],
            "email": list[2],
            "date": list[3],
        }
        commitgraph.append(commit)

    commitgraph.reverse()

    gitshowcommand = "git show {}:{}".format(commitgraph[0]['hash'],filename)

    show = subprocess.run(gitshowcommand, shell=True, capture_output=True, text=True)
    unparsed_show = show.stdout
    count = len(unparsed_show.split('\n'))

    #remember to change index 0 to null; line0 = index 0
    scoreboard = [commitgraph[0]["author"]] * (count + 1)

    #print scoreboard
    #for i in range(1,len(scoreboard)):
        #print("{} : {}".format(i, scoreboard[i]))

    for i in range(len(commitgraph)-1):
    #for i in range(2):
        commithash0 = commitgraph[i]['hash']
        commithash1 = commitgraph[i+1]['hash']
        #print("{} Doing hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        gitdiffcommand = "git diff -U0 --numstat {} {} -- {}".format(commithash0,commithash1,filename)

        diff = subprocess.run(gitdiffcommand, shell=True, capture_output=True, text=True)
        unparsed_diff = diff.stdout
        #print(unparsed_diff)
        unparsed_diff = unparsed_diff.split("\n")
        #print(unparsed_diff[-1])
        start1 = 0
        start2 = 0

        queue1 = []
        queue2 = []

        negcurr = 0
        balance = 0

        for x in range(6, len(unparsed_diff)):
        #for x in range(6, len(unparsed_diff)):
            if len(unparsed_diff[x]) == 0 or unparsed_diff[x][0] == "@":
                while(queue1 or queue2):
                    if(queue1 and queue2 and queue1[0]["line"] == queue2[0]["line"]):
                        #do listen algo here
                        #current I set as who edited last
                        scoreboard[queue1[0]["line"]] = commitgraph[i+1]['author']
                        #print("Edited line {}".format(queue1[0]["line"]))
                        queue1.pop(0)
                        queue2.pop(0)
                    elif(queue1):
                        lineToStartPoppingAt = queue1[0]["line"]
                        while(queue1):
                                scoreboard.pop(lineToStartPoppingAt)
                                #print("Deleted line {}".format(lineToStartPoppingAt))
                                balance-=1
                                queue1.pop(0)
                                #print("Scoreboard len: {}".format(len(scoreboard)))
                    elif(queue2):
                        scoreboard.insert(queue2[0]["line"], commitgraph[i+1]['author'])
                        #print("Added on line {}".format(queue2[0]["line"]))
                        balance+=1
                        queue2.pop(0)
                    else:
                        print("Something went wrong while testing even")
                #print("Scoreboard len: {}".format(len(scoreboard)))

                if(len(unparsed_diff[x]) != 0):
                    start1, start2 = getStarts(unparsed_diff[x])
            elif unparsed_diff[x][0] == "-":
                queue1.append({"line":start1+balance, "content": unparsed_diff[1:]})
                start1+=1
            elif unparsed_diff[x][0] == "+":
                queue2.append({"line":start2, "content": unparsed_diff[1:]})
                start2+=1
            
        #print("Round{} Scoreboard for hash0: {} and hash1: {}".format(i,commithash0,commithash1))
        #for i in range(1,len(scoreboard)):
            #print("{} : {}".format(i, scoreboard[i]))
    dict = {}
    for i in range(1, len(scoreboard)):
        author = scoreboard[i]

        if author in dict.keys():
            #key exists
            dict[author] += 1
        else:
            dict[author] = 1

    prefix = "{} Scoreboard: [ ".format(filename)

    result = ', '.join(f'{key}: {value}' for key, value in dict.items())
    print(prefix + result + " ]")

    #for d in dict:
        #print("{}: {}%".format(d, dict[d]/len(scoreboard)))

    
