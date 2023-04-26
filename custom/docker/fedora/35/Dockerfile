ARG ARCH=
FROM ${ARCH}fedora:35

# The support for Fedora Linux ended on December 13, 2022.
# The package repository has been moved to http://archives.fedoraproject.org.
RUN sed -i 's/metalink=/#metalink=/g' /etc/yum.repos.d/*
RUN sed -i 's/#baseurl=/baseurl=/g' /etc/yum.repos.d/*
RUN sed -i 's/download.example\/pub/archives.fedoraproject.org\/pub\/archive/g' /etc/yum.repos.d/*
