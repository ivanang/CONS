"""
Dinh, John
Ng, Ivana
CPSC 097

CON$:  A concurrency control mechanism for Dropbox
Command line interface adapted from Dropbox Python SDK
"""

import cmd
import locale
import os
import pprint
import shlex
import sys

from Tkinter import *
from tkFileDialog import *
from dropbox import client, rest, session
from time import gmtime, strptime, mktime, time

from textEditor import *

APP_KEY = ''
APP_SECRET = ''
ACCESS_TYPE = 'dropbox' 

def command(login_required=True):
    """a decorator for handling authentication and exceptions"""
    def decorate(f):
        def wrapper(self, args):
            if login_required and not self.sess.is_linked():
                self.stdout.write("Please 'login' to execute this command\n")
                return

            try:
                return f(self, *args)
            except TypeError, e:
                self.stdout.write(str(e) + '\n')
            except rest.ErrorResponse, e:
                msg = e.user_error_msg or str(e)
                self.stdout.write('Error: %s\n' % msg)

        wrapper.__doc__ = f.__doc__
        return wrapper
    return decorate

class DropboxTerm(cmd.Cmd):
    def __init__(self, app_key, app_secret):
        cmd.Cmd.__init__(self)
        self.sess = StoredSession(app_key, app_secret, access_type=ACCESS_TYPE)
        self.api_client = client.DropboxClient(self.sess)
        self.current_path = ''
        self.prompt = "Dropbox> "
        self.username = ""
        self.uid = ""
        self.lockStartTime = ""

        #in minutes
        self.timeLimit = 5
        
        self.sess.load_creds()
        #self.setName()

    @command()
    def do_pwd(self):
      """
      Prints current directory
      """
      self.stdout.write(self.current_path)
      self.stdout.write("\n")

    @command()
    def do_ls(self):
        """list files in current remote directory"""
        resp = self.api_client.metadata(self.current_path)

        if 'contents' in resp:
            for f in resp['contents']:
                name = os.path.basename(f['path'])
                encoding = locale.getdefaultlocale()[1]
                self.stdout.write(('%s\n' % name))#.encode(encoding))

    @command()
    def do_cd(self, path):
        """change current working directory"""
        if path == "..":
            self.current_path = "/".join(self.current_path.split("/")[0:-1])
        else:
            self.current_path += "/" + path

    @command(login_required=False)
    def do_login(self):
        """log in to a Dropbox account"""
        try:
            self.sess.link()
        except rest.ErrorResponse, e:
            self.stdout.write('Error: %s\n' % str(e))

    @command()
    def do_logout(self):
        """log out of the current Dropbox account"""
        self.sess.unlink()
        self.current_path = ''

    @command()
    def do_cat(self, path):
        """display the contents of a file"""
        f = self.api_client.get_file(self.current_path + "/" + path)
        self.stdout.write(f.read())
        self.stdout.write("\n")

    @command()
    def do_mkdir(self, path):
        """create a new directory"""
        self.api_client.file_create_folder(self.current_path + "/" + path)

    @command()
    def do_rm(self, path):
        """delete a file or directory"""
        self.api_client.file_delete(self.current_path + "/" + path)

    @command()
    def do_mv(self, from_path, to_path):
        """move/rename a file or directory"""
        self.api_client.file_move(self.current_path + "/" + from_path,
                                  self.current_path + "/" + to_path)

    @command()
    def do_account_info(self):
        """display account information"""
        f = self.api_client.account_info()
        pprint.PrettyPrinter(indent=2).pprint(f)

    @command()
    def do_exit(self):
        """exit"""
        return True

    @command()
    def do_testGetPut(self, nameOfFile, n):
      """
      Runs a scripted test of getting and putting
      """
      from_path = "~/cs97/project/filler.dat"
      to_path = nameOfFile

      for i in range(int(n)):
        #PUT
        from_file = open(os.path.expanduser(from_path))
        bput = time()
        self.api_client.put_file(self.current_path + "/" + to_path, from_file)
        aput = time()
        diffPut = aput-bput

        p = open("putTimes2.log", 'a')
        p.write(str(diffPut))
        p.write("\n")
        p.close()

        #GET
        out = open(nameOfFile, 'w')
        bget = time()
        out.write(self.api_client.get_file(self.current_path + "/" + \
            nameOfFile).read())
        aget = time()
        out.close()

        diff = aget - bget

        g = open("getTimes2.log", 'a')
        g.write(str(diff))
        g.write("\n")
        g.close()

        #REMOVE PUT FILE
        self.api_client.file_delete(self.current_path + "/" + nameOfFile)

    @command()
    def do_put(self, from_path, to_path):
        """
        Copy local file to Dropbox

        Examples:
        Dropbox> put ~/test.txt dropbox-copy-test.txt
        """
        from_file = open(os.path.expanduser(from_path))
        self.api_client.put_file(self.current_path + "/" + to_path, from_file)

    @command()
    def do_get(self, nameOfFile):
      """
      Gets a file
      """
      out = open(nameOfFile, 'w')
      out.write(self.api_client.get_file(self.current_path + "/" + \
          nameOfFile).read())
      out.close()

    @command()
    def do_testPutVerifyLock(self, nameOfFile, n):
      """
      Tests the times for putting and verifying a lock
      """

      for i in range(int(n)):
        p = open("labPutLockTimes.log", 'a')
        tBeforeLock = time()
        lockFilename = self.putLock(nameOfFile)
        tAfterLock = time()
        putDiff = tAfterLock - tBeforeLock
        p.write(str(putDiff))
        p.write("\n")
        p.close()

        v = open("labVerifyLockTimes.log", 'a')
        tBeforeVerify = time()
        haveLock = self.verifyLock(lockFilename)
        tAfterVerify = time()
        verifyDiff = tAfterVerify - tBeforeVerify
        v.write(str(verifyDiff))
        v.write("\n")
        v.close()

        self.removeAllLocks(lockFilename)

    @command()
    def do_testDummy(self, nameOfFile, n):
      """
      Does verifyLock but with a False return
      """
      h = self.putLock(nameOfFile)

      for i in range(int(n)):
        v = open("labFalseVerifyTimes.log", 'a')
        tb = time()
        haveLock = self.verifyLock(".lock.hello.txt")
        ta = time()

        td = ta-tb
        v.write(str(td))
        v.write("\n")
        v.close()
      self.removeAllLocks(".lock.hello.txt")



    @command()
    def do_open(self, nameOfFile):
      """
      When inside the same directory and given a filename, downloads the file
      into the local directory where CON$ is run
      """
      #Put a lock
      lockFilename = self.putLock(nameOfFile)

      #Verify the lock
      haveLock = self.verifyLock(lockFilename)

      #If lock verified, go get the file.
      if haveLock:

        #Prepare a local copy and stream in the Dropbox copy
        out = open(nameOfFile, 'w')
        out.write(self.api_client.get_file(self.current_path + "/" + \
            nameOfFile).read())
        out.close()

        #open the file in our awesome text editor
        root = Tk()
        editor = TextEditor(root, nameOfFile, self.api_client, \
            self.timeLimit, self.current_path)
        editor.countdown()
        editor.isExpired()
        editor.checkOtherUsers()
        root.mainloop()
        
        #after the user finishes editing, checks to see if file was modified
        #if so, syncs it back
        if editor.hasChanged():
          f = open(os.path.expanduser(nameOfFile))
          self.api_client.put_file(self.current_path + "/" + nameOfFile, \
              f, overwrite=True)
        os.remove(nameOfFile)
        self.removeAllLocks(lockFilename)

      else:
        timeFound = self.getTimeInLock(nameOfFile)

        if self.isExpired(timeFound):
          lock2 = self.putLock(lockFilename[1:])
          haveLock2 = self.verifyLock(lockFilename[1:])
          if haveLock2:
            #then you can delete the 'lockFilename'
            self.removeAllLocks(lockFilename)
            self.stdout.write("Trying opening the file again!\n")
          else:
            self.stdout.write("Someone else has permission to delete the lock\
                try again soon!\n")
        else:
          self.stdout.write("You do not have the lock.  Try again later!\n")

    @command()
    def do_help(self):
        # Find every "do_" attribute with a non-empty docstring and print
        # out the docstring.
        all_names = dir(self)
        cmd_names = []
        for name in all_names:
            if name[:3] == 'do_':
                cmd_names.append(name[3:])
        cmd_names.sort()
        for cmd_name in cmd_names:
            f = getattr(self, 'do_' + cmd_name)
            if f.__doc__:
                self.stdout.write('%s: %s\n' % (cmd_name, f.__doc__))

    # the following are for command line magic and aren't Dropbox-related
    def emptyline(self):
        pass

    def do_EOF(self, line):
        self.stdout.write('\n')
        return True

    def parseline(self, line):
        parts = shlex.split(line)
        if len(parts) == 0:
            return None, None, line
        else:
            return parts[0], parts[1:], line

    def removeAllLocks(self, lockFilename):
      """
      After a lock is released, cleans up all the locks
      """
      parts = lockFilename.split(".")
      parts = parts[1:-1]
      resp = self.api_client.metadata(self.current_path)

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
      toRemove = []
      for m in matches:
        if m[0:lenCompare] == compare:
          toRemove.append(m)
      
      #performs the removal of matching locks
      for r in toRemove:
        self.api_client.file_delete(self.current_path + "/" + r)


    def isExpired(self, timeFound):
      """
      Given a time, will check to see if a lease is expired or not
      Returns True if yes, False if no.
      """
      now = gmtime()
      other = strptime(timeFound, "%a, %d %b %Y %H:%M:%S +0000")

      timeDiff = mktime(now) - mktime(other)

      if (timeDiff / 60.0) > self.timeLimit:
        return True

      return False

    def getTimeInLock(self, nameOfFile):
      """
      This method will get the time listed in a lockFile
      """
      lockSign = ".lock."
      lockFilename = lockSign + nameOfFile
      
      #opens the lockFile locally to stream in information
      out = open(lockFilename, 'w')
      out.write(self.api_client.get_file(self.current_path + "/" + \
            lockFilename).read())
      out.close()

      #Reads the date
      out = open(lockFilename, 'r')
      lines = out.readlines()
      time = lines[2].strip()
      out.close()
      
      #cleans the local lockFile
      os.remove(lockFilename)

      #print "The time found in", lockFilename, "is", time

      return time

    def setName(self):
      """
      Sets the name and UID of the dropbox user as data in the object
      """
      info = self.api_client.account_info()
      self.username = info["display_name"]
      self.uid = str(info["uid"])

    def putLock(self, filename):
      """
      Puts a lock
      """
      lockSign = ".lock."

      #creates the lock file locally (because it has to be uploaded!)
      lockFilename = lockSign + filename
      LF = open(lockFilename, "w")

      #writes the user's name into the lockfile
      LF.write(self.username)
      LF.write("\n")
      LF.write(self.uid)
      LF.write("\n")
      LF.close()
      
      #opens the stream for the lockFile
      #puts the lockfile in the dropbox
      lockFile = open(os.path.expanduser(lockFilename))
      meta = self.api_client.put_file(self.current_path + "/" + lockFilename, \
          lockFile)

      lockFile.close()
      
      #set the lockStartTime
      self.lockStartTime = meta["modified"]

      #parse the path to get the name of our file
      path = meta["path"]
      pathList = path.split("/")
      lockFilenameReturned = pathList[-1]


      #opens the lockFile locally to stream in information
      out = open(lockFilename, 'w')
      out.write(self.api_client.get_file(self.current_path + "/" + \
            lockFilenameReturned).read())

      #writes the lockStartTime
      out.write(self.lockStartTime)
      out.write("\n")
      out.close()

      #puts the lockFile back into Dropbox
      #sets overwrite to True and allows us to avoid having to delete the old
      #lockFile
      lockFile = open(os.path.expanduser(lockFilename))
      self.api_client.put_file(self.current_path + "/" + lockFilenameReturned, \
          lockFile, overwrite=True)

      #deletes the local lockfile so that we do not have conflicting copies
      #when we go through verification
      os.remove(lockFilename)

      #return the name of the lockFile
      return lockFilename

    def verifyLock(self, lockFilename):
      """
      Given a lockFilename, goes and downloads that lock file.
      If the user id inside matches the name associated with this instance of 
      the application, then returns True.  Otherwise, False.
      """

      #Prepares a local file to receive the contents of the lockFile
      #Reads in the lockFile
      out = open(lockFilename, 'w')
      out.write(self.api_client.get_file(self.current_path + "/" + \
          lockFilename).read())
      out.close()

      #Reads the UID
      out = open(lockFilename, 'r')
      lines = out.readlines()
      uid = lines[1].strip()
      out.close()

      #Cleans up the local lockFile
      os.remove(lockFilename)

      #Gives True if you have the lock
      #False if you do not have the lock
      if str(uid) == self.uid:
        return True
      else:
        return False


class StoredSession(session.DropboxSession):
    """a wrapper around DropboxSession that stores a token to a file on disk"""
    TOKEN_FILE = "token_store.txt"

    def load_creds(self):
        try:
            stored_creds = open(self.TOKEN_FILE).read()
            self.set_token(*stored_creds.split('|'))
            print "[loaded access token]"
        except IOError:
            pass # don't worry if it's not there

    def write_creds(self, token):
        f = open(self.TOKEN_FILE, 'w')
        f.write("|".join([token.key, token.secret]))
        f.close()

    def delete_creds(self):
        os.unlink(self.TOKEN_FILE)

    def link(self):
        request_token = self.obtain_request_token()
        url = self.build_authorize_url(request_token)
        print "url:", url
        print "Please authorize in the browser. After you're done, press enter."
        raw_input()

        self.obtain_access_token(request_token)
        self.write_creds(self.token)

    def unlink(self):
        self.delete_creds()
        session.DropboxSession.unlink(self)

def main():
    if APP_KEY == '' or APP_SECRET == '':
        exit("You need to set your APP_KEY and APP_SECRET!")
    term = DropboxTerm(APP_KEY, APP_SECRET)
    term.cmdloop()

if __name__ == '__main__':
    main()
