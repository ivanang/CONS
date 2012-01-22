from Tkinter import *
from tkFileDialog import *
from dropbox import *
import os
from time import *

"""
This is the main code for a text editor that communicates over dropbox
"""

class TextEditor:
  def __init__(self, root, nameOfFile, client, timeLimit, currPath):
    self.timeLimit = timeLimit
    self.timePassed = 0
    self.currentPath = currPath
    self.client = client
    account = client.account_info()
    self.user = account["display_name"]

    self.root = root
    self.root.title(nameOfFile + " - CON$")

    self.currentFilename = nameOfFile


    frame = Frame(master=root, width=1024, height=512)
    frame.pack()
    
    self.textBox = Text(master=root, height=24, width=80, font="courier")
    self.scroll = Scrollbar(root)
    self.scroll.pack(side=RIGHT,fill=Y)
    self.textBox.configure(yscrollcommand = self.scroll.set)
    self.textBox.pack()
    self.cursor = self.textBox.index(INSERT)

    self.syncButton = Button(frame, text="Sync to Dropbox", fg="black",\
        command=self.syncToDropbox)
    self.syncButton.pack(side=LEFT)

    self.quitButton = Button(frame, text="Quit", fg="black", \
        command=root.destroy)
    self.quitButton.pack(side=RIGHT, padx=20)

    self.names = StringVar()
    self.names.set("Other users:  None")
    self.otherUsersLabel = Label(root, textvariable=self.names, fg="black")
    self.otherUsersLabel.pack(padx=20)

    #self.menu = self.createMenu(root)

    self.openLocal()

    self.modified = False
    self.hasExpired = False
    self.otherUsers = False

  def createMenu(self, root):
    """
    Creates a the menu for our text editor
    """

    menu = Menu(root)
    root.config(menu=menu)

    filemenu = Menu(menu)
    menu.add_cascade(label="File",menu=filemenu)
    
    filemenu.add_command(label="Save",command=self.saveLocal)
   
    #editmenu = Menu(menu)
    #menu.add_cascade(label="Edit",menu=editmenu)
    #editmenu.add_command(label="Sample",command=self.testCallback)
    #editmenu.add_command(label="Sample",command=self.testCallback)

  def increaseLease(self):
    """
    Increases the lease by 5 minutes
    """
    self.timeLimit += 5

  def openLocal(self):
    """
    Opens a local file and displays it in the text environment
    """

    fhandle = open(self.currentFilename)
    lines = fhandle.read()
    self.textBox.delete(1.0,END)
    self.textBox.insert(INSERT,lines)

  def saveLocal(self):
    """
    Saves whatever is in the textBox
    """
    f = open(self.currentFilename, "w")
    content = self.textBox.get(1.0, END)
    f.write(content)
    self.modified = True

    f.close()

  def syncToDropbox(self):
    """
    When the user clicks 'sync back to dropbox,' will sync the file back
    to dropbox without quitting the editor
    """
    self.saveLocal()
    
    f = open(os.path.expanduser(self.currentFilename))
    self.client.put_file(self.currentPath + "/" + self.currentFilename, \
        f, overwrite=True)
    f.close()

  def hasChanged(self):
    """
    Returns True if the file has been modified and saved,
    False otherwise.
    """
    if self.modified == True: 
      return True
    else: 
      return False

  def testCallback(self):
    """
    Dummy callback function
    """
    print "Someone has clicked!"

  def countdown(self):
    """
    Counts down the timer
    """
    if self.cursor == self.textBox.index(CURRENT):
      self.timePassed += 1
    else:
      self.timePassed = 0
      self.cursor = self.textBox.index(CURRENT)

    if (self.timePassed/60) > self.timeLimit:
      self.hasExpired = True
      return

    self.textBox.after(1000, self.countdown)
    

  def isExpired(self):
    """
    If lease is expired, closes the program
    """

    if self.hasExpired == True:
      self.modified == False
      self.root.quit()

    self.textBox.after(1000, self.isExpired)

  def checkOtherUsers(self):
    """
    Finds other lockfiles and displays the names of the users who want to
    work
    """
    lockFilename = ".lock." + self.currentFilename
    parts = lockFilename.split(".")
    parts = parts[1:-1]
    resp = self.client.metadata(self.currentPath)
    filenames = []
    allLockfiles = []

    #populates a list of all the files in the current directory
    if 'contents' in resp:
      for f in resp['contents']:
          name = os.path.basename(f['path'])
          filenames.append(name)

    #finds anything that is a lock
    matches = []
    for f in filenames:
      if f[0:5] == ".lock":
        matches.append(f)
 
    compare = ".".join(parts)
    compare = "." + compare

    lenCompare = len(compare)

    #makes sure that the locks we're removing are for the same file
    toCheck = []
    for m in matches:
      if m[0:lenCompare] == compare:
        toCheck.append(m)
      
    names = []

    #performs the removal of matching locks
    for c in toCheck:
      #Prepares a local file to receive the contents of the lockFile
      #Reads in the lockFile
      out = open(c, 'w')
      out.write(self.client.get_file(self.currentPath + "/" + \
          c).read())
      out.close()

      #Reads the username
      out = open(c, 'r')
      lines = out.readlines()
      name = lines[0].strip()
      if name != self.user:
        names.append(name)

      out.close()

      #Cleans up the local lockFile
      os.remove(c)
    
    nameString = ""
    if len(names) > 0:
      for name in names:
        nameString = nameString + name + " "

      self.names.set("Users who would like to work on this file: " + nameString)

    self.textBox.after(10000, self.checkOtherUsers)


def main():
  sess = session.DropboxSession('9vbg2a7xxnfa5md', '34biszx8n8gqbhc', \
        'dropbox')

  t = open("token.txt").read()
  sess.set_token(*t.split('|'))

  cli = client.DropboxClient(sess)

  root = Tk()
  c = TextEditor(root,"thingsToDo.txt", cli, 0, "/test")
  c.checkOtherUsers()
  c.countdown()
  c.isExpired()

  root.mainloop()

if __name__ == '__main__':
    main()

