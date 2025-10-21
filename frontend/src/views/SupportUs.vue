<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">
        <v-card class="pa-6" elevation="2">
          <v-card-title class="d-flex align-center mb-4">
            <h2 class="text-h4 font-weight-bold">Support Kiwix</h2>
            <img src="/assets/logo.svg" width="32" height="32" class="ml-2" alt="CMS Logo" />
          </v-card-title>

          <v-card-text class="text-body-1">
            <p class="mb-4">
              CMS is
              <a href="https://kiwix.org" target="_blank" class="text-primary text-decoration-none">
                Kiwix</a
              >'s platform for automating the management of
              <a
                href="https://wiki.openzim.org/wiki/ZIM_File_Format"
                target="_blank"
                class="text-primary text-decoration-none"
              >
                ZIM files</a
              >
              publication. Every ZIMs created on the
              <a
                href="https://farm.openzim.org"
                target="_blank"
                class="text-primary text-decoration-none"
              >
                Zimfarm</a
              >go through the CMS for quality checks before publication to our libraries and
              download servers. All day, every day, so you can enjoy offline content.
            </p>

            <v-card variant="outlined" class="mb-4">
              <v-card-title class="text-h6">
                <v-icon class="mr-2">mdi-heart</v-icon>
                Support with Donations
              </v-card-title>
              <v-card-text>
                <p class="mb-0">
                  It is <strong>entirely and only supported by donations</strong>. A few dollars may
                  not mean much for you but will certainly help us a lot: if you can,
                  <a
                    href="https://support.kiwix.org/"
                    target="_blank"
                    class="text-primary text-decoration-none"
                  >
                    consider supporting us
                  </a>
                  — even with the price of a cup of coffee (we love coffee and at times need quite a
                  bit of it).
                </p>
              </v-card-text>
            </v-card>

            <v-divider class="my-2"></v-divider>

            <p>
              CMS is a Python and Vue.JS project hosted
              <a
                href="https://github.com/openzim/cms"
                target="_blank"
                class="text-primary text-decoration-none"
              >
                on Github</a
              >.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts"></script>

<style scoped>
.v-card-title h2 {
  margin: 0;
}
</style>
