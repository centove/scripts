#!/usr/bin/perl -wT
#-*-perl-*-

=pod

=head1 SYNOPSIS

B<ipcalc> I<host> [netmask] 

=head1 DESCRIPTION

B<ipcalc> provides network calcualtions about an IP address

=cut

use strict;
use Net::Netmask;
use Socket;

my ($VERSION)          = '$Revision: 1.0 $' =~ /([.\d]+)/;
my $warnings           = 0;

$SIG {__WARN__}        = sub {          # Print a usuage message on an unknown
    if ( substr (                       # option.  Borrowed from abigail.
   $_ [0], 
   0, 
   14
  ) eq "Unknown option" ) { die "Usage" };
    require File::Basename;
    $0                 = File::Basename::basename ( $0 );
    $warnings          = 1;
    warn "$0: @_";
};

$SIG {__DIE__} = sub {
    require File::Basename;
    $0                 = File::Basename::basename ( $0 );
    if ( substr ( 
   $_ [0], 
   0,  
   5
  ) eq "Usage" ) {
        die <<EOF;
$0 (Perl bin utils) $VERSION
$0 address [netmask]
EOF
    }
    die "$0: @_";
};

die "Usage"
  unless $ARGV[0];

my (
    $foo,
    $corge
    )              = ipSanity ( $ARGV[0] );

my $profferedMask  = $ARGV[1] || $corge;

=pod

=head1 EXAMPLES

Provide information about a network

 C:\home\idnopheq\scripts>ipcalc 192.168.1.0 255.255.255.0
 CIDR        = 192.168.1.0/24
 net addr    = 192.168.1.0
 mask        = 255.255.255.0 ffffff00
 hostmask    = 0.0.0.255
 mask bits   = 24
 net size    = 256
 max mask    = 24
 bcast       = 192.168.1.255
 next net    = 192.168.2.0
 first host  = 192.168.1.1
 last host   = 192.168.1.254

or

 C:\home\idnopheq\scripts>ipcalc 192.168.1.128/25
 CIDR        = 192.168.1.128/25
 net addr    = 192.168.1.128
 mask        = 255.255.255.128 ffffff80
 hostmask    = 0.0.0.127
 mask bits   = 25
 net size    = 128
 max mask    = 25
 bcast       = 192.168.1.255
 next net    = 192.168.2.0
 first host  = 192.168.1.129
 last host   = 192.168.1.254

Provide information about a host

 C:\home\idnopheq\scripts>ipcalc 192.168.1.100
 CIDR        = 192.168.1.100/32
 net addr    = 192.168.1.100
 mask        = 255.255.255.255 ffffffff
 hostmask    = 0.0.0.0
 mask bits   = 32
 net size    = 1
 net pos :0      dot dec:192.168.1.100
 hex addr:c0a80164     dec addr:3232235876
 bin addr:11000000101010000000000101100100

=cut

my $block          = new Net::Netmask($foo,                  # address
                                      $profferedMask         # netmask dec-dot
                                     );
my $inetAddr       = $block->base();
my $mask           = $block->mask();
my $pos            = $block->match ( $foo ) + 0;
print "CIDR, SIZE\n";
print  $block->desc() ,", ";
print "net addr    = " , $inetAddr           , "\n";
print "mask        = " , $mask               , " ";
print unpack ( 
       'H8H8H8H8', 
       inet_aton ( $mask )
      ) , "\n";
print "hostmask    = " , $block->hostmask()  , "\n";
print "mask bits   = " , $block->bits()      , "\n";

if ( $block->size() != 1 ){
  print "max mask    = " , $block->maxblock()  , "\n";
  print "bcast       = " , $block->broadcast() , "\n";
  print "next net    = " , $block->next()      , "\n";
  print "first host  = " , $block->nth(1)      , "\n";
  print "last host   = " , $block->nth(-2)     , "\n";
}

exit;

if ( $inetAddr ne $foo || $block->size() == 1 ) {
  print "net pos :" , $pos , "\t";
  print "dot dec:" , $foo , "\n";
  print "hex addr:" , unpack ( 
         'H8H8H8H8', 
         inet_aton ( $foo )
        ) , "     ";
  print "dec addr:" , unpack ( 
         'N8N8N8N8',
         inet_aton ( $foo )
        ) , "\n";
  print "bin addr:" , unpack ( 
         'B8B8B8B8', 
         inet_aton ( $foo )
        ) , "\n";
}

=head1 ENVIRONMENT

The working of B<ipcalc> is not influenced by any environment variables.

=cut

sub ipSanity {
  my $ip                    = shift;
  my $count                 = 0;
  my $separator             = ' ';
  my $mask;

  $separator                = '/'
    if $ip                  =~ /\//;
  $separator                = ':'
    if $ip                  =~ /:/;

  (
   $ip,
   $mask
  )                         = split /$separator/, $ip
    if $separator ne ' ';

  $mask                     = int2quad ( imask ( $mask ) )
    if $separator           =~ /\//;

  $count++
    while $ip               =~ /\./g;

  die "Invalid format $ip!\n"
    if ( $count != 3 && $ip =~ /:/ );

  my (
      $baz,
      $bitMask,
      $netMask
      );

  while ( $count < 3 ) {
    $ip                    .= ".0";
    $count++;
  }
  unless ( $ip              =~         # sanity check the $remote IP address
    m{                          # this is so cool, I'm still disecting
      ^  ( \d | [01]?\d\d | 2[0-4]\d | 25[0-5] )
     \.  ( \d | [01]?\d\d | 2[0-4]\d | 25[0-5] )
     \.  ( \d | [01]?\d\d | 2[0-4]\d | 25[0-5] )
     \.  ( \d | [01]?\d\d | 2[0-4]\d | 25[0-5] )
  $                             # from the Perl Cookbook, Recipe 6.23,
       }xo                             # pages 218-9, as fixed in the 01/00
   ) {                          # reprint
    die "Invalid IP address $ip!\n";
  }
  return ( 
   $ip,
   $mask
  );
}

sub imask {
  return (2**32 -(2** (32- $_[0])));
}

sub int2quad {
  return join('.',unpack('C4', pack("N", $_[0])));
}

__END__

=pod

=head1 BUGS

B<ipcalc> suffers from no known bugs at this time.

Believed to work on Windows NT, Windows 2K, Solaris, Linux, and NetBSD.
Anywhere Net::Netmask will install.

=head1 REVISION HISTORY

    ipcalc
    Revision 1.0  2001/05/03 10:34:03  idnopheq
    Initial revision

=head1 AUTHOR

The Perl implementation of B<ipcalc> was written by Dexter Coffin,
I<idnopheq@home.com>.

=head1 COPYRIGHT and LICENSE

Copyright 2001 Dexter Coffin. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY DEXTER COFFIN ``AS IS'' AND ANY EXPRESS
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DEXTER COFFIN BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are
those of the author and should not be interpreted as representing official
policies, either expressed or implied, anywhere.

=head1 SEE ALSO

=head1 NEXT TOPIC

=cut
