-- MySQL dump 10.14  Distrib 5.5.32-MariaDB, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: events
-- ------------------------------------------------------
-- Server version	5.5.32-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `wmii_client`
--

DROP TABLE IF EXISTS `wmii_client`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wmii_client` (
  `client_id` int(11) NOT NULL AUTO_INCREMENT,
  `id` varchar(15) NOT NULL,
  `session_id` int(11) NOT NULL,
  `program` text NOT NULL,
  `xclass` text NOT NULL,
  PRIMARY KEY (`client_id`),
  KEY `session_id` (`session_id`),
  CONSTRAINT `wmii_client_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `wmii_session` (`session_id`)
) ENGINE=InnoDB AUTO_INCREMENT=205 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wmii_client_label`
--

DROP TABLE IF EXISTS `wmii_client_label`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wmii_client_label` (
  `client_id` int(11) NOT NULL,
  `label_time` datetime(6) NOT NULL,
  `label` text NOT NULL,
  KEY `client_id` (`client_id`),
  CONSTRAINT `wmii_client_label_ibfk_1` FOREIGN KEY (`client_id`) REFERENCES `wmii_client` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wmii_focus_event`
--

DROP TABLE IF EXISTS `wmii_focus_event`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wmii_focus_event` (
  `session_id` int(11) NOT NULL,
  `client_id` int(11) NOT NULL,
  `focus_time` datetime(6) NOT NULL,
  KEY `session_id` (`session_id`),
  KEY `client_id` (`client_id`),
  CONSTRAINT `wmii_focus_event_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `wmii_session` (`session_id`),
  CONSTRAINT `wmii_focus_event_ibfk_2` FOREIGN KEY (`client_id`) REFERENCES `wmii_client` (`client_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wmii_session`
--

DROP TABLE IF EXISTS `wmii_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `wmii_session` (
  `session_id` int(11) NOT NULL AUTO_INCREMENT,
  `start_time` datetime NOT NULL,
  PRIMARY KEY (`session_id`)
) ENGINE=InnoDB AUTO_INCREMENT=93 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2013-09-14 16:44:19
